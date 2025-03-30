"""
Kubernetes & ArgoCD Platform API - Main Application

This FastAPI application serves as a unified API for interacting with Kubernetes
and ArgoCD, supporting both direct operations and pass-through proxy capabilities.
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

# Import our modules
from kubernetes_api import router as kubernetes_router
from argocd_api import router as argocd_router, get_argocd_token
from tvp import router as tvp_router, start_reconciliation_thread
from config import get_settings, get_k8s_client

app = FastAPI(
    title="Kubernetes Platform API",
    description="A unified API for Kubernetes and ArgoCD operations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers from different modules
app.include_router(kubernetes_router, prefix="/k8s", tags=["Kubernetes"])
app.include_router(argocd_router, prefix="/argocd", tags=["ArgoCD"])
app.include_router(tvp_router, prefix="/tvp", tags=["TVP"])

@app.on_event("startup")
async def startup_event():
    """
    Runs when the application starts.
    Initializes background tasks like the GitOps reconciliation thread.
    """
    # Start the TVP GitOps reconciliation thread
    start_reconciliation_thread()

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint providing basic platform information."""
    return {
        "name": "Kubernetes Platform API",
        "description": "Unified API for Kubernetes and ArgoCD operations",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": [
            {"prefix": "/k8s", "description": "Kubernetes API operations"},
            {"prefix": "/argocd", "description": "ArgoCD API operations"},
            {"prefix": "/tvp", "description": "Thinnest Viable Platform operations"}
        ]
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint that verifies connectivity to Kubernetes and ArgoCD services.
    """
    health_status = {
        "status": "healthy",
        "services": {
            "kubernetes": {"status": "unknown"},
            "argocd": {"status": "unknown"}
        }
    }
    
    # Check Kubernetes connectivity
    try:
        k8s_client = get_k8s_client()
        k8s_client.list_namespace()  # Removed timeout_seconds parameter
        health_status["services"]["kubernetes"] = {
            "status": "healthy"
        }
    except Exception as e:
        health_status["services"]["kubernetes"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check ArgoCD connectivity
    settings = get_settings()
    try:
        # Use the helper function we created for ArgoCD auth
        token = await get_argocd_token()
        if token:
            health_status["services"]["argocd"] = {
                "status": "healthy"
            }
        else:
            health_status["services"]["argocd"] = {
                "status": "unhealthy",
                "error": "Failed to get authentication token"
            }
            health_status["status"] = "degraded"
    except HTTPException as e:
        health_status["services"]["argocd"] = {
            "status": "unhealthy",
            "error": e.detail
        }
        health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["argocd"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
