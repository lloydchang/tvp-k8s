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
    try:
        # Simple command to check if kubectl can connect to the cluster
        process = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "name"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3
        )
        
        is_healthy = process.returncode == 0
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "message": process.stdout if is_healthy else process.stderr
        }
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}

async def check_argo_cd_health() -> Dict[str, Any]:
    """Check the health of the ArgoCD server."""
    settings = get_settings()
    try:
        # Check if ArgoCD server URL is configured
        if not settings.argo_cd_server_url:
            return {"status": "unconfigured", "message": "ArgoCD server URL not configured"}
        
        # Parse the URL correctly, handling various formats
        parsed_url = settings.argo_cd_server_url
        if "://" in parsed_url:
            parsed_url = parsed_url.split("://")[1]
        if ":" in parsed_url:
            parsed_url = parsed_url.split(":")[0]
            
        # Try to connect to ArgoCD server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((parsed_url, 443))
        sock.close()
        
        is_healthy = result == 0
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "message": f"ArgoCD server at {settings.argo_cd_server_url} is {'reachable' if is_healthy else 'unreachable'}"
        }
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for the API and its dependent services.
    """
    settings = get_settings()
    services_status = {}
    overall_status = "healthy"
    
    # Check Kubernetes connection
    services_status["kubernetes"] = await check_kubernetes_health()
    if services_status["kubernetes"]["status"] != "healthy":
        overall_status = "degraded"
    
    # Check Argo CD connection
    services_status["argo_cd"] = await check_argo_cd_health()
    if services_status["argo_cd"]["status"] != "healthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "services": services_status
    }
