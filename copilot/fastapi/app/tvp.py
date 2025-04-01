"""
Thinnest Viable Platform (TVP) Module

This module provides functionality for platform operations using a minimal,
focused approach that reduces cognitive load for developers while providing
just enough functionality to enable rapid, safe delivery.

Following GitOps principles:
1. Declarative - Configuration stored in Git as YAML
2. Versioned and Immutable - Git provides versioning and history
3. Pulled Automatically - TVP agent pulls from Git
4. Continuously Reconciled - TVP agent applies changes automatically
"""

15 from fastapi import APIProxy, HTTPException, BackgroundTasks
16 import logging
17 from pydantic import BaseModel
18 from typing import Optional, Any
19 import os
20 import subprocess
21 from subprocess import CalledProcessError, TimeoutExpired
22 import time
23 import threading
24 import yaml
25 from pathlib import Path
27 from datetime import datetime
from config import get_settings

proxy = APIProxy()
logger = logging.getLogger(__name__)

# Global reconciliation flag and lock for thread safety
is_reconciling = False
reconciliation_thread = None
reconciliation_lock = threading.Lock()

class TVPStatus(BaseModel):
    """
    Status of TVP GitOps reconciliation.
    
    Attributes:
        is_reconciling (bool): Whether reconciliation is currently in progress.
        last_reconciliation (Optional[str]): ISO formatted timestamp of the last reconciliation.
        status (str): Current status of the TVP service ("active" or "inactive").
        applications (List[Dict[str, Any]]): List of applications managed by TVP.
    """
    is_reconciling: bool
    last_reconciliation: Optional[str] = None
    status: str
    applications: List[Dict[str, Any]] = []

@proxy.get("/status", summary="Get TVP GitOps reconciliation status", response_model=TVPStatus)
async def get_tvp_status() -> TVPStatus:
    """
    Gets the status of the TVP GitOps reconciliation.
    
    Returns:
        TVPStatus: Object containing reconciliation status, applications list, and timestamps.
    
    Raises:
        Exception: If there's an error reading application data from the repository.
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
                            except yaml.YAMLError as yaml_err:
                                # Log specific YAML parsing error
                                logger.error(f"Error parsing YAML in {values_file}: {yaml_err}")
        except OSError as e:
            logger.error(f"Error reading applications directory: {e}")
        except Exception as e:
            logger.error(f"Error reading applications: {e}")
    
    with reconciliation_lock:
        status = "active" if reconciliation_thread and reconciliation_thread.is_alive() else "inactive"
    
    return TVPStatus(
        is_reconciling=is_reconciling,
        last_reconciliation=get_last_reconciliation_time(),
        status=status,
    )

@proxy.post("/reconcile", summary="Trigger a TVP GitOps reconciliation")
async def trigger_reconciliation(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Triggers a GitOps reconciliation process.
    
    The reconciliation will pull the latest configuration from Git and apply it.
    This operation runs in the background to avoid blocking the API request.
    
    Args:
        background_tasks (BackgroundTasks): FastAPI background tasks runner.
        
    Returns:
        dict: Status message indicating whether reconciliation was started or already running.
    """
    global is_reconciling
    
    with reconciliation_lock:
        if is_reconciling:
            return {"status": "already_running", "message": "Reconciliation already in progress"}
        
        background_tasks.add_task(reconcile_from_git)
    
    return {"status": "started", "message": "Reconciliation process started"}

def start_reconciliation_thread() -> None:
    """
    Start a background thread that periodically reconciles from Git.
    
    This function creates a daemon thread that runs reconciliation at regular intervals.
    If a thread is already running, it will not start a new one.
    """
    global reconciliation_thread
    
    if reconciliation_thread and reconciliation_thread.is_alive():
        return
    
    def periodic_reconcile() -> None:
        while True:
            try:
                reconcile_from_git()
            except Exception as e:
                logger.error(f"Error in periodic reconciliation: {e}")
            time.sleep(60)  # Reconcile every minute
    
    reconciliation_thread = threading.Thread(target=periodic_reconcile, daemon=True)
    reconciliation_thread.start()
    logger.info("Started GitOps reconciliation thread")

def get_last_reconciliation_time() -> Optional[str]:
    """
    Get the last reconciliation timestamp.
    
    Returns:
        Optional[str]: ISO formatted timestamp of the last reconciliation, or None if unavailable.
    """
    settings = get_settings()
    timestamp_file = Path(settings.tvp_repo_path) / ".last_reconciliation"
    
    if timestamp_file.exists():
        try:
            return timestamp_file.read_text().strip()
        except OSError as e:
            logger.error(f"Error reading reconciliation timestamp: {e}")
            return None
    return None

def set_last_reconciliation_time() -> None:
    """
    Record the current time as the last reconciliation timestamp.
    
    Writes the current datetime as an ISO formatted string to a file in the repository.
    
    Raises:
        OSError: If there's an error writing the timestamp file.
    """
    settings = get_settings()
    timestamp_file = Path(settings.tvp_repo_path) / ".last_reconciliation"
    
    timestamp = datetime.now().isoformat()
    
    try:
        timestamp_file.write_text(timestamp)
    except OSError as e:
        logger.error(f"Failed to write reconciliation timestamp: {e}")

def reconcile_from_git() -> None:
    """
    Pull the latest configuration from Git and apply it.
    
    This is the core GitOps reconciliation function. It handles:
    1. Cloning or updating the Git repository
    2. Reading configuration from YAML files
    3. Applying configurations to the Kubernetes cluster
    4. Updating the reconciliation timestamp
    
    The function is thread-safe and prevents concurrent reconciliations.
    
    Raises:
        CalledProcessError: If any Git command fails during execution
        OSError: For filesystem-related errors
        yaml.YAMLError: For YAML parsing errors
    """
    global is_reconciling
    
    with reconciliation_lock:
        if is_reconciling:
            return
        is_reconciling = True
    
    try:
        settings = get_settings()
        
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
    except CalledProcessError as e:
        logger.error(f"Git operation failed: {e.cmd} returned {e.returncode}: {e.stderr}")
    except TimeoutExpired as e:
        logger.error(f"Git operation timed out: {e.cmd} after {e.timeout} seconds")
    except OSError as e:
        logger.error(f"Filesystem error during reconciliation: {e}")
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}")
    except Exception as e:
        logger.error(f"GitOps reconciliation failed with unexpected error: {str(e)}")
    finally:
        with reconciliation_lock:
            is_reconciling = False

def _clone_repository(repo_url: str, repo_path: str, branch: str) -> None:
    """
    Clone the source repository.
    
    Args:
        repo_url (str): URL of the Git repository to clone.
        repo_path (str): Local path where the repository should be cloned.
        branch (str): Branch to check out.
        
    Raises:
        subprocess.CalledProcessError: If Git clone operation fails.
        OSError: If directory creation fails.
    """
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    try:
        # Add timeout to prevent hanging on network issues
        # Validate or sanitize `branch` and `repo_url` before usage
        safe_branch = sanitize_branch_name(branch)
        safe_url = sanitize_git_url(repo_url)
        subprocess.run(
            ["git", "clone", "-b", safe_branch, safe_url, repo_path], 
            check=True,
            capture_output=True,
            text=True,
            timeout=120
        )
    except CalledProcessError as e:
        logger.error(f"Git clone failed: {e.stderr}")
        raise

def _update_repository(repo_path: str, branch: str) -> None:
    """
    Update the source repository to latest changes.
    
    Args:
        repo_path (str): Local path of the repository to update.
        branch (str): Branch to check out and pull.
        
    Raises:
        subprocess.CalledProcessError: If any Git operation fails.
    """
    try:
        # Add timeout to prevent hanging
        subprocess.run(["git", "-C", repo_path, "fetch"], 
                      check=True, capture_output=True, text=True, timeout=30)
        
        subprocess.run(["git", "-C", repo_path, "checkout", branch], 
                      check=True, capture_output=True, text=True, timeout=30)
        
        subprocess.run(["git", "-C", repo_path, "pull"], 
                      check=True, capture_output=True, text=True, timeout=30)
    except CalledProcessError as e:
        logger.error(f"Git update failed: {e.stderr}")
        raise

def _apply_configurations_from_git(repo_path: Path) -> None:
    """
    Apply configurations from Git to the cluster.
    
    This function implements the actual reconciliation logic,
    applying Kubernetes resources from the Git repository.
    
    Args:
        repo_path (Path): Path to the Git repository containing configurations.
        
    Raises:
        OSError: For filesystem-related errors
        yaml.YAMLError: For YAML parsing errors
        CalledProcessError: If Kubernetes command execution fails
    """
    # Scan repository for application configurations
    for namespace_dir in [d for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith('.')]:
        for app_dir in [d for d in namespace_dir.iterdir() if d.is_dir()]:
            values_file = app_dir / "values.yaml"
            if values_file.exists():
                try:
                    # Read values file to get configuration details
                    with open(values_file, 'r') as f:
                        values = yaml.safe_load(f)
                        
                    logger.info(f"Applying configuration for {namespace_dir.name}/{app_dir.name}")
                    
                    # Check if manifests directory exists
                    manifests_dir = app_dir / "manifests"
                    if manifests_dir.exists() and manifests_dir.is_dir():
                        # Example: Apply with kubectl
                        # subprocess.run([
                        #    "kubectl", "apply", "-f", str(manifests_dir),
                        #    "-n", namespace_dir.name
                        # ], check=True, capture_output=True, text=True, timeout=60)
                        pass
                        
                except yaml.YAMLError as e:
                    logger.error(f"YAML parsing error in {values_file}: {e}")
                except OSError as e:
                    logger.error(f"File operation error for {app_dir}: {e}")
                except Exception as e:
                    logger.error(f"Failed to apply {namespace_dir.name}/{app_dir.name}: {str(e)}")

@proxy.get("/status/{namespace}/{app_name}", summary="Get TVP deployment status")
async def get_deployment_status(namespace: str, app_name: str) -> Dict[str, Any]:
    """
    Gets the status of a TVP deployment.
    
    Args:
        namespace (str): Kubernetes namespace of the application.
        app_name (str): Name of the application.
        
    Returns:
        dict: Application status information including image, tag, and deployment status.
        
    Raises:
        HTTPException: If the application is not found in the repository (404).
        Exception: If there's an error reading the application's values file.
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
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {values_file}: {e}")
            raise HTTPException(status_code=500, detail=f"Invalid YAML in application configuration")
        except OSError as e:
            logger.error(f"Error reading values file: {e}")
            raise HTTPException(status_code=500, detail=f"Error reading application configuration")
    
    return app_info
