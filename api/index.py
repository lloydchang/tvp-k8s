"""
TVP API

This FastAPI application serves as a unified API for interacting with Kubernetes
and Argo CD, supporting both direct operations and pass-through proxy capabilities.

The application provides:
- Health checking for dependent services 
- GitOps to Deploy and Reconcile 
- Argo CD API pass-through and operations 
- Kubernetes API pass-through and operations 
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import contextlib

# Fix imports to use python.app modules instead of app modules
from python.app.gitops import proxy as gitops_router, start_reconciliation_thread
from python.app.argo_cd_api import proxy as argo_cd_proxy, get_argo_cd_token
from python.app.kubernetes_api import proxy as kubernetes_proxy
from python.app.config import get_settings, get_kubernetes_client

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs at startup
    try:
        start_reconciliation_thread()
    except Exception as e:
        print(f"Failed to start reconciliation thread: {e}")
    yield
    # Cleanup if needed at shutdown

app = FastAPI(
    title="TVP API",
    description="Thinnest Viable Platform API",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Health"},
        {"name": "GitOps", "description": "GitOps to Deploy and Reconcile Microservices"},
        {"name": "Argo CD", "description": "Argo CD"},
        {"name": "Kubernetes", "description": "Kubernetes"}
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add static file mounting for UI
import os
from pathlib import Path

# Try to handle both local development and serverless environments
static_dir = os.environ.get("STATIC_FILES_DIR", None)
if not static_dir:
    # Attempt to find the UI directory relative to this file
    # For local development
    local_ui = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui")
    # For Vercel deployment
    vercel_ui = os.path.join(os.path.dirname(__file__), "static")
    
    if os.path.isdir(local_ui):
        static_dir = local_ui
    elif os.path.isdir(vercel_ui):
        static_dir = vercel_ui
    else:
        # Fallback to a UI directory next to the code
        static_dir = os.path.join(os.path.dirname(__file__), "ui")

# Only mount if the directory exists
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="ui_static")
else:
    print(f"Warning: Static files directory not found at {static_dir}")

# Create a single router for GitOps
gitops_api_router = APIRouter()

# Include the gitops router (no need to specify tags again as they're already in the router)
gitops_api_router.include_router(
    gitops_router  # Removed redundant tags=["GitOps"]
)

# Include the routers with their respective prefixes
app.include_router(gitops_api_router, prefix="/gitops")
app.include_router(argo_cd_proxy, prefix="/argo/cd", tags=["Argo CD"])
app.include_router(kubernetes_proxy, prefix="/kubernetes", tags=["Kubernetes"])

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
            {"prefix": "/gitops", "description": "GitOps to Deploy and Reconcile Microservices"},
            {"prefix": "/argo/cd", "description": "Argo CD"},
            {"prefix": "/kubernetes", "description": "Kubernetes"},
            {"name": "UI", "description": "User Interface"},
        ]
    }

@app.get("/ui", response_class=HTMLResponse, tags=["UI"])
async def ui_root():
    """Serve the UI homepage."""
    # Read the content of the UI HTML file
    import os
    ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "index.html")
    with open(ui_path, "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint that verifies connectivity to Kubernetes and Argo CD services.
    
    Performs live checks against dependent services to determine if the application
    is fully operational.
    
    Returns:
        dict: Health status containing overall status and individual service states.
        
        Service states can be:
        - "healthy": Service is responding properly
        - "unhealthy": Service is unreachable or responding with errors
        - "unknown": Service status could not be determined
        
        Overall status can be:
        - "healthy": All services are healthy
        - "degraded": One or more services are unhealthy
    """
    settings = get_settings()
    health_status = {
        "status": "healthy",
        "services": {
            "kubernetes": {
                "status": "unknown",
            },
            "argo_cd": {
                "status": "unknown",
            }
        }
    }
    
    # Check Kubernetes connectivity
    try:
        client = get_kubernetes_client()
        # Simply list namespaces to check connectivity
        namespaces = client.list_namespace()
        health_status["services"]["kubernetes"]["status"] = "healthy"
    except Exception as e:
        health_status["services"]["kubernetes"]["status"] = "unhealthy"
        health_status["services"]["kubernetes"]["error"] = str(e)
        health_status["status"] = "degraded"
    
    # Check Argo CD connectivity
    try:
        token = await get_argo_cd_token()
        if token:
            health_status["services"]["argo_cd"]["status"] = "healthy"
        else:
            health_status["services"]["argo_cd"]["status"] = "unhealthy"
            health_status["services"]["argo_cd"]["error"] = "Failed to obtain Argo CD token"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["argo_cd"]["status"] = "unhealthy"
        health_status["services"]["argo_cd"]["error"] = str(e)
        health_status["status"] = "degraded"
        
    return health_status

def main():
    """Entry point for running the uvicorn server."""
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)

# This if statement allows for easier testing of the main function
# while still allowing it to be run as a script
if __name__ == "__main__":  # pragma: no cover
    main()
