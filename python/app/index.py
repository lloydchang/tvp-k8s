"""
Main application entry point that sets up the FastAPI app
and imports all API routers.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Dict, Any
import socket
import subprocess
import uvicorn

from .config import get_settings
from .kubernetes_api import proxy as kubernetes_router
from .argo_cd_api import proxy as argocd_router
from .gitops import proxy as gitops_router

# Create the FastAPI application
app = FastAPI(
    title="TVP Platform API",
    description="API for interacting with Kubernetes and Argo CD operations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add startup and shutdown event handlers
@app.on_event("startup")
async def startup():
    """Application startup tasks."""
    try:
        # Start GitOps reconciliation thread if configured
        from .gitops import start_reconciliation_thread
        await start_reconciliation_thread()
    except Exception as e:
        print(f"Failed to start reconciliation thread: {e}")
        # Just log error without failing app startup

@app.on_event("shutdown")
async def shutdown():
    """Application shutdown tasks."""
    # Any cleanup tasks can go here
    pass

# Include routers
app.include_router(kubernetes_router, prefix="/api/kubernetes", tags=["Kubernetes"])
app.include_router(argocd_router, prefix="/api/argocd", tags=["Argo CD"])
app.include_router(gitops_router, prefix="/api/gitops", tags=["GitOps"])

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint returning API information.
    """
    return {
        "message": "Welcome to the TVP Platform API",
        "version": "1.0.0",
        "endpoints": {
            "kubernetes": "/api/kubernetes",
            "argocd": "/api/argocd",
            "gitops": "/api/gitops",
            "health": "/health"
        }
    }

# Main function to run the app directly when the script is executed
def main():
    """
    Run the application directly using uvicorn when this script is executed.
    """
    uvicorn.run("app.index:app", host="0.0.0.0", port=8000, reload=True)

# Health check functions
async def check_kubernetes_health() -> Dict[str, Any]:
    """Check the health of the Kubernetes API server."""
    settings = get_settings()
    try:
        # Check if Kubernetes API URL is configured
        if not settings.kubernetes_api_url:
            return {
                "status": "unconfigured", 
                "message": "Kubernetes API URL not configured",
                "error": "Kubernetes API URL not configured"
            }
        
        # For development mode, use subprocess to call kubectl
        if settings.environment == "development":
            try:
                process = subprocess.run(["kubectl", "get", "nodes"], 
                                       capture_output=True, text=True, check=False)
                if process.returncode == 0:
                    return {
                        "status": "healthy", 
                        "message": "Connected to Kubernetes cluster",
                        "dev_mode": True
                    }
                else:
                    # Fallback to get more info for diagnostic purposes
                    try:
                        context = subprocess.run(["kubectl", "config", "current-context"],
                                              capture_output=True, text=True, check=False)
                        if context.returncode == 0:
                            return {
                                "status": "unhealthy", 
                                "message": f"Connected to context {context.stdout.strip()} but cannot access nodes",
                                "error": f"Cannot access nodes in context {context.stdout.strip()}",
                                "dev_mode": True
                            }
                    except Exception:
                        pass
                    return {
                        "status": "unhealthy", 
                        "message": "Could not connect using kubectl",
                        "error": "Could not connect using kubectl",
                        "dev_mode": True
                    }
            except FileNotFoundError:
                return {
                    "status": "unhealthy", 
                    "message": "No kubectl",
                    "error": "kubectl not found - Kubernetes tools not installed but optional in development mode",
                    "dev_mode": True
                }
            except Exception as e:
                return {
                    "status": "unhealthy", 
                    "message": str(e),
                    "error": f"Error with kubectl: {str(e)}. Kubernetes tools not installed but optional in development mode",
                    "dev_mode": True
                }
        
        # Use HTTP client to check API server
        async with httpx.AsyncClient(verify=settings.verify_ssl) as client:
            response = await client.get(f"{settings.kubernetes_api_url}/version", timeout=5)
            if response.status_code >= 200 and response.status_code < 300:
                return {"status": "healthy", "message": "Kubernetes API server is healthy"}
            else:
                return {
                    "status": "unhealthy", 
                    "message": f"Kubernetes API server returned status {response.status_code}",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
    except Exception as e:
        # Debug/Development mode should provide additional diagnostics
        if settings.environment == "development":
            try:
                # Try to get version info as diagnostic
                process = subprocess.run(["kubectl", "version", "--client"], 
                                       capture_output=True, text=True, check=False)
                if process.returncode == 0:
                    return {
                        "status": "healthy", 
                        "message": process.stdout.strip(),
                        "dev_mode": True
                    }
            except Exception:
                # Fallback for when kubectl is not available
                return {
                    "status": "unhealthy", 
                    "message": str(e),
                    "error": f"Kubernetes tools not installed but optional in development mode: {str(e)}",
                    "dev_mode": True
                }

        return {
            "status": "unhealthy", 
            "message": str(e),
            "error": str(e)
        }

async def check_argo_cd_health() -> Dict[str, Any]:
    """Check the health of the ArgoCD server."""
    settings = get_settings()
    try:
        # Check if ArgoCD server URL is configured
        if not settings.argo_cd_url:
            return {
                "status": "unconfigured", 
                "message": "ArgoCD server URL not configured",
                "error": "ArgoCD server URL not configured"
            }
        
        # In development mode, test connection differently
        if settings.environment == "development":
            try:
                # Parse the URL correctly, handling various formats
                parsed_url = settings.argo_cd_url
                port = 443
                if "://" in parsed_url:
                    parsed_url = parsed_url.split("://")[1]
                if ":" in parsed_url:
                    parts = parsed_url.split(":")
                    parsed_url = parts[0]
                    if len(parts) > 1 and parts[1].isdigit():
                        port = int(parts[1])
                
                # Try to connect to ArgoCD server
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((parsed_url, port))
                sock.close()
                
                if result == 0:
                    return {
                        "status": "healthy", 
                        "message": f"ArgoCD server at {settings.argo_cd_url} is reachable",
                        "dev_mode": True
                    }
                else:
                    return {
                        "status": "unhealthy", 
                        "message": f"ArgoCD server at {settings.argo_cd_url} is unreachable",
                        "error": f"Socket connection failed (error {result}) - ArgoCD is optional in development mode",
                        "dev_mode": True
                    }
            except Exception as e:
                return {
                    "status": "unhealthy", 
                    "message": str(e),
                    "error": f"Socket error in development mode: {str(e)} - ArgoCD is optional in development",
                    "dev_mode": True
                }
        
        # In production, use HTTP client to check API server
        if settings.argo_cd_url:
            async with httpx.AsyncClient(verify=settings.verify_ssl) as client:
                response = await client.get(f"{settings.argo_cd_url}/api/v1/version", timeout=5)
                # 200 OK or 401 Unauthorized are both acceptable (401 means ArgoCD requires auth)
                if response.status_code == 200 or response.status_code == 401:
                    return {"status": "healthy", "message": "ArgoCD server is healthy"}
                else:
                    return {
                        "status": "unhealthy", 
                        "message": f"ArgoCD server returned status {response.status_code}",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
        else:
            return {
                "status": "unhealthy", 
                "message": "ArgoCD URL not configured",
                "error": "ArgoCD URL not provided in configuration"
            }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "message": str(e),
            "error": str(e)
        }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for the API and its dependent services.
    """
    settings = get_settings()
    services_status = {}
    overall_status = "healthy"
    
    # Check Kubernetes connection
    try:
        services_status["kubernetes"] = await check_kubernetes_health()
        if services_status["kubernetes"]["status"] != "healthy":
            # In development mode, treat warnings as healthy for certain situations
            if settings.environment == "development" and "dev_mode" in services_status["kubernetes"]:
                # Override for development mode
                overall_status = "healthy"
            else:
                overall_status = "degraded"
    except Exception as e:
        services_status["kubernetes"] = {
            "status": "unhealthy", 
            "message": str(e),
            "error": f"Exception during health check: {str(e)}"
        }
        overall_status = "degraded"
    
    # Check Argo CD connection
    try:
        services_status["argo_cd"] = await check_argo_cd_health()
        if services_status["argo_cd"]["status"] != "healthy":
            # In development mode, ArgoCD is optional
            if settings.environment == "development" and "dev_mode" in services_status["argo_cd"]:
                # Override for development mode
                pass
            else:
                overall_status = "degraded"
    except Exception as e:
        services_status["argo_cd"] = {
            "status": "unhealthy", 
            "message": str(e),
            "error": f"Exception during health check: {str(e)}"
        }
        overall_status = "degraded"
    
    # In development mode, always return healthy
    if settings.environment == "development":
        overall_status = "healthy"
    
    return {
        "status": overall_status,
        "services": services_status
    }

# Run the application when the script is executed directly
if __name__ == "__main__":
    main()
