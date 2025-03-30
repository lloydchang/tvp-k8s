"""
Thinnest Viable Platform (TVP) Module

This module provides functionality for platform operations using a minimal, focused approach that reduces cognitive load for developers while providing just enough functionality to enable rapid, safe delivery.

Following GitOps principles:
1. Declarative - Configuration stored in Git as YAML
2. Versioned and Immutable - Git provides versioning and history
3. Pulled Automatically - TVP agent pulls from Git
4. Continuously Reconciled - TVP agent applies changes automatically
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import subprocess
import shutil
import time
import threading
import yaml
from pathlib import Path
import logging
from datetime import datetime

from config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Global reconciliation flag
is_reconciling = False
reconciliation_thread = None

class TVPStatus(BaseModel):
    """Status of TVP GitOps reconciliation"""
    is_reconciling: bool
    last_reconciliation: Optional[str] = None
    status: str
    applications: List[Dict[str, Any]] = []

@router.get("/status", summary="Get TVP GitOps reconciliation status")
async def get_tvp_status():
    """
    Gets the status of the TVP GitOps reconciliation.
    """
    settings = get_settings()
    
    # Get status about the Git repository
    repo_path = Path(settings.tvp_repo_path)
    
    applications = []
    
    if repo_path.exists():
        # List all namespaces directories
        try:
            for namespace_dir in [d for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith('.')]:
                for app_dir in [d for d in namespace_dir.iterdir() if d.is_dir()]:
                    values_file = app_dir / "values.yaml"
                    if values_file.exists():
                        with open(values_file, 'r') as f:
                            try:
                                values = yaml.safe_load(f)
                                applications.append({
                                    "app_name": app_dir.name,
                                    "namespace": namespace_dir.name,
                                    "image": values.get("image", "unknown"),
                                    "tag": values.get("tag", "unknown"),
                                })
                            except yaml.YAMLError:
                                # Skip invalid YAML files
                                pass
        except Exception as e:
            logger.error(f"Error reading applications: {e}")
    
    return TVPStatus(
        is_reconciling=is_reconciling,
        last_reconciliation=get_last_reconciliation_time(),
        status="active" if reconciliation_thread and reconciliation_thread.is_alive() else "inactive",
        applications=applications
    )

@router.post("/reconcile", summary="Trigger a TVP GitOps reconciliation")
async def trigger_reconciliation(background_tasks: BackgroundTasks):
    """
    Triggers a GitOps reconciliation process.
    The reconciliation will pull the latest configuration from Git and apply it.
    """
    global is_reconciling
    
    if is_reconciling:
        return {"status": "already_running", "message": "Reconciliation already in progress"}
    
    background_tasks.add_task(reconcile_from_git)
    
    return {"status": "started", "message": "Reconciliation process started"}

def start_reconciliation_thread():
    """Start a background thread that periodically reconciles from Git"""
    global reconciliation_thread
    
    if reconciliation_thread and reconciliation_thread.is_alive():
        return
    
    def periodic_reconcile():
        while True:
            reconcile_from_git()
            time.sleep(300)  # Reconcile every 5 minutes
    
    reconciliation_thread = threading.Thread(target=periodic_reconcile, daemon=True)
    reconciliation_thread.start()
    logger.info("Started GitOps reconciliation thread")

def get_last_reconciliation_time():
    """Get the last reconciliation timestamp"""
    settings = get_settings()
    timestamp_file = Path(settings.tvp_repo_path) / ".last_reconciliation"
    
    if timestamp_file.exists():
        try:
            return timestamp_file.read_text().strip()
        except:
            return None
    return None

def set_last_reconciliation_time():
    """Record the current time as the last reconciliation timestamp"""
    settings = get_settings()
    timestamp_file = Path(settings.tvp_repo_path) / ".last_reconciliation"
    
    timestamp = datetime.now().isoformat()
    
    try:
        timestamp_file.write_text(timestamp)
    except Exception as e:
        logger.error(f"Failed to write reconciliation timestamp: {e}")

def reconcile_from_git():
    """
    Pull the latest configuration from Git and apply it.
    This is the core GitOps reconciliation function.
    """
    global is_reconciling
    
    if is_reconciling:
        return
    
    is_reconciling = True
    settings = get_settings()
    
    try:
        # Ensure repo path exists
        repo_path = Path(settings.tvp_repo_path)
        
        # Clone/update the repository
        if not repo_path.exists():
            _clone_repository(settings.tvp_repo_url, settings.tvp_repo_path, settings.tvp_branch)
        else:
            _update_repository(settings.tvp_repo_path, settings.tvp_branch)
        
        # Apply configurations from Git to the cluster
        _apply_configurations_from_git(repo_path)
        
        # Update reconciliation timestamp
        set_last_reconciliation_time()
        
        logger.info("GitOps reconciliation completed successfully")
    except Exception as e:
        logger.error(f"GitOps reconciliation failed: {str(e)}")
    finally:
        is_reconciling = False

def _clone_repository(repo_url: str, repo_path: str, branch: str):
    """Clone the source repository."""
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    subprocess.run(["git", "clone", "-b", branch, repo_url, repo_path], check=True)

def _update_repository(repo_path: str, branch: str):
    """Update the source repository to latest changes."""
    subprocess.run(["git", "-C", repo_path, "fetch"], check=True)
    subprocess.run(["git", "-C", repo_path, "checkout", branch], check=True)
    subprocess.run(["git", "-C", repo_path, "pull"], check=True)

def _apply_configurations_from_git(repo_path: Path):
    """
    Apply configurations from Git to the cluster.
    This function would implement the actual reconciliation logic,
    applying Kubernetes resources from the Git repository.
    """
    # Scan repository for application configurations
    for namespace_dir in [d for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith('.')]:
        for app_dir in [d for d in namespace_dir.iterdir() if d.is_dir()]:
            values_file = app_dir / "values.yaml"
            if values_file.exists():
                try:
                    # Apply this application's configuration
                    # In a real implementation, this might:
                    # 1. Use Helm to install/upgrade the application
                    # 2. Apply kubectl manifests
                    # 3. Use the Kubernetes API to create/update resources
                    logger.info(f"Applying configuration for {namespace_dir.name}/{app_dir.name}")
                    
                    # Example: Apply with kubectl
                    # subprocess.run([
                    #    "kubectl", "apply", "-f", str(app_dir / "manifests"),
                    #    "-n", namespace_dir.name
                    # ], check=True)
                except Exception as e:
                    logger.error(f"Failed to apply {namespace_dir.name}/{app_dir.name}: {str(e)}")

@router.get("/status/{namespace}/{app_name}", summary="Get TVP deployment status")
async def get_deployment_status(namespace: str, app_name: str):
    """
    Gets the status of a TVP deployment.
    """
    settings = get_settings()
    repo_path = Path(settings.tvp_repo_path)
    app_path = repo_path / namespace / app_name
    
    if not app_path.exists():
        raise HTTPException(status_code=404, detail=f"Application {app_name} not found in repository")
    
    values_file = app_path / "values.yaml"
    app_info = {
        "application": app_name,
        "namespace": namespace,
        "repository": settings.tvp_repo_url,
        "status": "unknown"
    }
    
    if values_file.exists():
        try:
            with open(values_file, 'r') as f:
                values = yaml.safe_load(f)
                app_info.update({
                    "image": values.get("image", "unknown"),
                    "tag": values.get("tag", "unknown"),
                    "last_reconciliation": get_last_reconciliation_time()
                })
                
                # In a real implementation, we would check the actual deployment status in the cluster
                # For now, we'll just assume it's deployed if it's in the repo
                app_info["status"] = "deployed"
        except Exception as e:
            logger.error(f"Error reading values file: {e}")
    
    return app_info
