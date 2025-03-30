"""
Kubernetes & ArgoCD Platform API - Main Application

This FastAPI application serves as a unified API for interacting with Kubernetes
and ArgoCD, supporting both direct operations and pass-through proxy capabilities.
"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import our modules
from kubernetes_api import router as kubernetes_router
from argocd_api import router as argocd_router
from gitops import router as gitops_router
from config import get_settings

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
app.include_router(gitops_router, prefix="/gitops", tags=["GitOps"])

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
            {"prefix": "/gitops", "description": "GitOps deployment operations"}
        ]
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
