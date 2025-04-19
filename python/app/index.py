"""
Main application entry point that sets up the FastAPI app
and imports all API routers.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Dict, Any
import socket

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

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for the API and its dependent services.
    """
    settings = get_settings()
    services_status = {}
    overall_status = "healthy"
    
    # Check Kubernetes connection
    services_status["kubernetes"] = {"status": "healthy"}
    try:
        # In development mode, be more tolerant of missing Kubernetes
        if settings.environment == "development":
            import subprocess
            import json
            import os
            
            # Check if kubectl is available
            try:
                # Try kubectl get nodes with a short timeout first
                kubectl_proc = subprocess.run(
                    ["kubectl", "get", "nodes", "--request-timeout=2s"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                
                if kubectl_proc.returncode == 0:
                    # Successfully connected to Kubernetes
                    services_status["kubernetes"] = {
                        "status": "healthy",
                        "message": "Connected to Kubernetes cluster"
                    }
                else:
                    # Kubernetes is not accessible, show context info
                    context_proc = subprocess.run(
                        ["kubectl", "config", "current-context"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    
                    context = context_proc.stdout.strip() if context_proc.returncode == 0 else "unknown"
                    
                    services_status["kubernetes"] = {
                        "status": "unhealthy",
                        "error": f"Cannot connect to Kubernetes context '{context}'. In development mode, this is optional.",
                        "dev_mode": True
                    }
            except (subprocess.SubprocessError, FileNotFoundError):
                services_status["kubernetes"] = {
                    "status": "unhealthy",
                    "error": "Kubernetes tools not available or properly configured. In development mode, this is optional.",
                    "dev_mode": True
                }
        else:
            # In production, we use the standard HTTP client approach
            async with httpx.AsyncClient(verify=settings.verify_ssl, timeout=5.0) as client:
                response = await client.get(f"{settings.kubernetes_api_url}/api/v1/namespaces")
                if response.status_code != 200:
                    services_status["kubernetes"] = {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    overall_status = "degraded"
    except Exception as e:
        # Only mark as degraded in production
        if settings.environment != "development":
            overall_status = "degraded"
            
        services_status["kubernetes"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check Argo CD connection
    services_status["argo_cd"] = {"status": "healthy"}
    try:
        # Special handling for development environment
        if settings.environment == "development":
            # In development, being unable to connect to Argo CD is acceptable
            # Mark as degraded but with a clear message that it's optional in dev
            try:
                # Parse URL - handle both http://hostname:port and hostname formats
                argo_url = settings.argo_cd_url
                if "://" in argo_url:
                    argo_host = argo_url.split("://")[1].split(":")[0]
                    port_str = argo_url.split(":")[-1]
                    port = int(port_str) if port_str.isdigit() else 80
                else:
                    argo_host = argo_url
                    port = 80
                
                # Try both localhost and configured host in dev mode
                hosts_to_try = ["localhost", argo_host]
                for host in hosts_to_try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2.0)  # Shorter timeout
                    result = sock.connect_ex((host, port))
                    sock.close()
                    if result == 0:  # Connection successful
                        break
                else:  # No successful connection
                    services_status["argo_cd"] = {
                        "status": "unhealthy",
                        "error": "Argo CD not available in development environment (optional)"
                    }
                    # Don't mark overall as degraded in dev for Argo CD
            except Exception as e:
                services_status["argo_cd"] = {
                    "status": "unhealthy",
                    "error": f"Argo CD connection check error in development: {str(e)}"
                }
                # Don't mark overall as degraded in dev for Argo CD
        else:
            # In production, try the actual API
            async with httpx.AsyncClient(verify=settings.verify_ssl, timeout=5.0) as client:
                response = await client.get(f"{settings.argo_cd_url}/api/v1/applications")
                if response.status_code not in (200, 401):  # 401 is fine, just means we need auth
                    services_status["argo_cd"] = {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    overall_status = "degraded"
    except Exception as e:
        if settings.environment != "development":
            overall_status = "degraded"
        services_status["argo_cd"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return {
        "status": overall_status,
        "services": services_status
    }
