"""
Kubernetes & Argo CD Platform API - Main Application

This FastAPI application serves as a unified API for interacting with Kubernetes
and Argo CD, supporting both direct operations and pass-through proxy capabilities.

The application provides:
- Kubernetes API pass-through and operations 
- Argo CD API pass-through and operations
- TVP GitOps reconciliation functionality
- Health checking for dependent services
"""

from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware
import httpx

# Import our modules
from app.kubernetes_api import proxy as kubernetes_proxy
from app.argo_cd_api import proxy as argo_cd_proxy, get_argo_cd_token
from app.tvp import proxy as tvp, start_reconciliation_thread
from app.config import get_settings, get_kubernetes_client

app = FastAPI(
    title="Kubernetes Platform API",
    description="A unified API for Kubernetes and Argo CD operations",
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
app.include_router(kubernetes_proxy, prefix="/kubernetes", tags=["Kubernetes"])
app.include_router(argo_cd_proxy, prefix="/argo/cd", tags=["Argo CD"])
app.include_router(tvp, prefix="/tvp", tags=["TVP"])

@app.on_event("startup")
async def startup_event():
    """
    Runs when the application starts.
    
    Initializes background tasks like the GitOps reconciliation thread.
    This ensures the TVP reconciliation process begins automatically
    when the API service starts.
    """
    # Start the TVP GitOps reconciliation thread
    start_reconciliation_thread()

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint providing basic platform information.
    
    Returns:
        dict: Information about the platform API including name, version,
              status, and available endpoints.
    """
    return {
        "name": "Kubernetes Platform API",
        "description": "Unified API for Kubernetes and Argo CD operations",
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
