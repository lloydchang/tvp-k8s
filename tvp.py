"""
Thinnest Viable Platform (TVP) Module

This module provides functionality for platform operations using a minimal,
focused approach that reduces cognitive load for developers while providing
just enough functionality to enable rapid, safe delivery.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import subprocess
import shutil
from pathlib import Path

from config import get_settings

router = APIRouter()

class TVPDeploymentRequest(BaseModel):
    app_name: str
    namespace: str
    image: str
    tag: str
    values: Optional[Dict[str, Any]] = None

@router.post("/deploy", summary="Deploy an application using the Thinnest Viable Platform")
async def deploy_application(deployment: TVPDeploymentRequest):
    """
    Deploys an application using the Thinnest Viable Platform approach.
    
    The TVP focuses on minimal viable capabilities that enable developers to deploy
    applications without unnecessary cognitive load.
    
    1. Updates configuration in the source repository
    2. Triggers automated deployment processes
    3. Minimizes developer effort through sensible defaults
    """
    settings = get_settings()
    
    # Ensure repo path exists
    repo_path = Path(settings.tvp_repo_path)
    
    try:
        # Clone/update the repository
        if not repo_path.exists():
            _clone_repository(settings.tvp_repo_url, settings.tvp_repo_path, settings.tvp_branch)
        else:
            _update_repository(settings.tvp_repo_path, settings.tvp_branch)
        
        # Update application configuration
        app_path = repo_path / deployment.namespace / deployment.app_name
        if not app_path.exists():
            raise HTTPException(status_code=404, detail=f"Application {deployment.app_name} not found in repository")
        
        # Update values files
        values_file = app_path / "values.yaml"
        if values_file.exists():
            _update_values_file(values_file, deployment.image, deployment.tag, deployment.values)
        
        # Commit and push changes
        _commit_and_push(settings.tvp_repo_path, f"Update {deployment.app_name} to {deployment.image}:{deployment.tag}")
        
        return {
            "status": "success",
            "message": f"TVP deployment initiated for {deployment.app_name}",
            "details": {
                "repository": settings.tvp_repo_url,
                "branch": settings.tvp_branch,
                "application": deployment.app_name,
                "namespace": deployment.namespace,
                "image": f"{deployment.image}:{deployment.tag}"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TVP deployment failed: {str(e)}")

def _clone_repository(repo_url: str, repo_path: str, branch: str):
    """Clone the source repository."""
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    subprocess.run(["git", "clone", "-b", branch, repo_url, repo_path], check=True)

def _update_repository(repo_path: str, branch: str):
    """Update the source repository to latest changes."""
    subprocess.run(["git", "-C", repo_path, "fetch"], check=True)
    subprocess.run(["git", "-C", repo_path, "checkout", branch], check=True)
    subprocess.run(["git", "-C", repo_path, "pull"], check=True)

def _update_values_file(file_path: str, image: str, tag: str, custom_values: Optional[Dict[str, Any]] = None):
    """Update the values file with new image and tag."""
    # In a real implementation, you would use a proper YAML parser
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update image and tag
    content = content.replace("image: oldimage", f"image: {image}")
    content = content.replace("tag: oldtag", f"tag: {tag}")
    
    with open(file_path, 'w') as f:
        f.write(content)

def _commit_and_push(repo_path: str, commit_message: str):
    """Commit changes and push to remote repository."""
    subprocess.run(["git", "-C", repo_path, "add", "."], check=True)
    subprocess.run(["git", "-C", repo_path, "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "-C", repo_path, "push"], check=True)

@router.get("/status/{namespace}/{app_name}", summary="Get TVP deployment status")
async def get_deployment_status(namespace: str, app_name: str):
    """
    Gets the status of a TVP deployment.
    """
    settings = get_settings()
    
    # Simple status check - would integrate with actual deployment systems in production
    return {
        "status": "deployed",
        "application": app_name,
        "namespace": namespace,
        "repository": settings.tvp_repo_url,
        "last_updated": "2023-01-01T00:00:00Z"
    }
