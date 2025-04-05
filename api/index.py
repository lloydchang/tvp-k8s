"""
TVP API

This FastAPI application serves as a unified API for interacting with Kubernetes
and Argo CD, supporting both direct operations and pass-through proxy capabilities.

The application provides:
- Kubernetes API pass-through and operations 
- Argo CD API pass-through and operations
- TVP GitOps reconciliation functionality
- Health checking for dependent services
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import contextlib

# Fix imports to use python.app modules instead of app modules
from python.app.kubernetes_api import proxy as kubernetes_proxy
from python.app.argo_cd_api import proxy as argo_cd_proxy, get_argo_cd_token
from python.app.tvp import proxy as tvp, start_reconciliation_thread
from python.app.config import get_settings, get_kubernetes_client

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs at startup
    start_reconciliation_thread()
    yield
    # Cleanup if needed at shutdown

app = FastAPI(
    title="TVP API",
    description="Thinnest Viable Platform API",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(kubernetes_proxy, prefix="/kubernetes", tags=["Kubernetes"])
app.include_router(argo_cd_proxy, prefix="/argo/cd", tags=["Argo CD"])
app.include_router(tvp, prefix="/tvp", tags=["TVP"])

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint providing basic platform information.
    
    Returns:
        dict: Information about the platform API including name, version,
              status, and available endpoints.
    """
    return {
        "name": "TVP API",
        "description": "Thinnest Viable Platform API",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": [
            {"prefix": "/kubernetes", "description": "Kubernetes API operations"},
            {"prefix": "/argo/cd", "description": "Argo CD API operations"},
            {"prefix": "/tvp", "description": "Thinnest Viable Platform operations"}
        ]
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint that verifies connectivity to Kubernetes and Argo CD services.
    
    Performs live checks against dependent services to determine
    if the application is fully operational.
    
    Returns:
        dict: Health status containing overall status and individual 
              service states.
              
    Service states can be:
    - "healthy": Service is responding properly
    - "unhealthy": Service is unreachable or responding with errors
    - "unknown": Service status could not be determined
    
    Overall status can be:
    - "healthy": All services are healthy
    - "degraded": One or more services are unhealthy
    """
    health_status = {
        "status": "healthy",
        "services": {
            "kubernetes": {"status": "unknown"},
            "argo_cd": {"status": "unknown"}
        }
    }
    
    # Check Kubernetes connectivity
    try:
        kubernetes_client = get_kubernetes_client()
        # Add timeout for the API call to prevent hanging
        kubernetes_client.list_namespace(timeout_seconds=5)
        health_status["services"]["kubernetes"] = {
            "status": "healthy"
        }
    except Exception as e:
        health_status["services"]["kubernetes"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Argo CD connectivity
    try:
        # Use the helper function we created for Argo CD auth
        token = await get_argo_cd_token()
        if token:
            health_status["services"]["argo_cd"] = {
                "status": "healthy"
            }
        else:
            health_status["services"]["argo_cd"] = {
                "status": "unhealthy",
                "error": "Failed to get authentication token"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["argo_cd"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
