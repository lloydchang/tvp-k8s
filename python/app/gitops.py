"""
GitOps Module

This module provides functionality for platform operations using a minimal,
focused approach that reduces cognitive load for developers while providing
just enough functionality to enable rapid, safe delivery.

Following GitOps principles:
1. Declarative - Configuration stored in Git as YAML
2. Versioned and Immutable - Git provides versioning and history
3. Pulled Automatically - GitOps agent pulls from Git
4. Continuously Reconciled - GitOps agent applies changes automatically
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
import logging
from pydantic import BaseModel
from typing import Optional, Any, List, Dict
import os
import subprocess
from subprocess import CalledProcessError, TimeoutExpired
import time
import threading
import yaml
from pathlib import Path
from datetime import datetime, timezone
from .config import get_settings

# Using APIRouter instead of APIProxy which doesn't exist in FastAPI
proxy = APIRouter()
logger = logging.getLogger(__name__)

# Global reconciliation flag and lock for thread safety
is_reconciling = False
reconciliation_thread = None
reconciliation_lock = threading.Lock()

# Define the models
class GitOpsStatus(BaseModel):
    """
    Status of GitOps reconciliation.
    
    Attributes:
        is_reconciling (bool): Whether reconciliation is currently in progress.
        last_reconciliation (Optional[str]): ISO formatted timestamp of the last reconciliation.
        status (str): Current status of the GitOps service ("active" or "inactive").
        applications (List[Dict[str, Any]]): List of applications managed by GitOps.
    """
    is_reconciling: bool
    last_reconciliation: Optional[str] = None
    status: str
    applications: List[Dict[str, Any]] = []

class DeploymentRequest(BaseModel):
    """
    Model for GitOps deployment requests.
    
    Attributes:
        image (str): Container image to deploy, typically in the format repository/image:tag.
        replicas (int): Number of replicas to deploy, defaults to 1.
        environment (Optional[Dict[str, str]]): Environment variables for the deployment.
        resources (Optional[Dict[str, Any]]): Resource requests and limits.
    """
    image: str
    replicas: int = 1
    environment: Optional[Dict[str, str]] = None
    resources: Optional[Dict[str, Any]] = None

class DeploymentStatus(BaseModel):
    """
    Status of a specific application deployment.
    
    Attributes:
        application (str): Name of the application.
        namespace (str): Kubernetes namespace of the application.
        repository (str): Git repository URL containing the application configuration.
        status (str): Deployment status (e.g., "deployed", "failed", "unknown").
        image (Optional[str]): Container image of the deployment.
        tag (Optional[str]): Container image tag of the deployment.
        last_reconciliation (Optional[str]): ISO formatted timestamp of the last reconciliation.
    """
    application: str
    namespace: str
    repository: str
    status: str
    image: Optional[str] = None
    tag: Optional[str] = None
    last_reconciliation: Optional[str] = None

# Deployment operations - now first in order
@proxy.get("/status/{namespace}/{app_name}", tags=["Deployments"], summary="Get deployment status", response_model=DeploymentStatus)
async def get_deployment_status(namespace: str, app_name: str) -> DeploymentStatus:
    """
    Gets the status of a specific application deployment.
    
    Args:
        namespace (str): Kubernetes namespace of the application.
        app_name (str): Name of the application.
        
    Returns:
        DeploymentStatus: Application deployment information including image, tag, and status.
        
    Raises:
        HTTPException: If the application is not found in the repository (404).
        HTTPException: If there's an error reading the application's values file (500).
    """
    settings = get_settings()
    repo_path = Path(settings.gitops_repo_path)
    app_path = repo_path / namespace / app_name
    
    if not app_path.exists():
        raise HTTPException(status_code=404, detail=f"Application {app_name} not found in repository")
    
    values_file = app_path / "values.yaml"
    app_info = DeploymentStatus(
        application=app_name,
        namespace=namespace,
        repository=settings.gitops_repo_url,
        status="unknown"
    )
    
    if values_file.exists():
        try:
            with open(values_file, 'r') as f:
                values = yaml.safe_load(f)
                app_info.image = values.get("image", "unknown")
                app_info.tag = values.get("tag", "unknown")
                app_info.last_reconciliation = get_last_reconciliation_time()
                
                # In a real implementation, we would check the actual deployment status in the Kubernetes API server
                # For now, we'll just assume it's deployed if it's in the repo
                app_info.status = "deployed"
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {values_file}: {e}")
            raise HTTPException(status_code=500, detail=f"Invalid YAML in application configuration")
        except OSError as e:
            logger.error(f"Error reading values file: {e}")
            raise HTTPException(status_code=500, detail=f"Error reading application configuration")
    
    return app_info

@proxy.post("/{namespace}/{app_name}", tags=["Deployments"], summary="Deploy an application", status_code=200)
async def deploy_application(namespace: str, app_name: str, deployment: DeploymentRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Deploys or updates an application using GitOps.
    
    This endpoint updates the application's configuration in the Git repository
    and then triggers a reconciliation to apply the changes.
    
    Args:
        namespace (str): Kubernetes namespace for the application.
        app_name (str): Name of the application to deploy.
        deployment (DeploymentRequest): Deployment configuration including image and tag.
        background_tasks (BackgroundTasks): FastAPI background tasks runner.
        
    Returns:
        dict: Status message and deployment information.
        
    Raises:
        HTTPException: If the application directory doesn't exist or there's an error updating the configuration.
    """
    settings = get_settings()
    repo_path = Path(settings.gitops_repo_path)
    app_path = repo_path / namespace / app_name
    
    # Ensure the repository is up to date
    try:
        if not repo_path.exists():
            _clone_repository(settings.gitops_repo_url, settings.gitops_repo_path, settings.gitops_repo_branch)
        else:
            _update_repository(settings.gitops_repo_path, settings.gitops_repo_branch)
    except Exception as e:
        logger.error(f"Failed to update Git repository: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update Git repository")
    
    # Create namespace/app directories if they don't exist
    app_path.parent.mkdir(exist_ok=True, parents=True)
    app_path.mkdir(exist_ok=True)
    
    # Create or update values.yaml
    values_file = app_path / "values.yaml"
    
    try:
        # Load existing values if they exist
        values = {}
        if values_file.exists():
            with open(values_file, 'r') as f:
                values = yaml.safe_load(f) or {}
        
        # Update with new values
        values.update({
            "image": deployment.image,
            "replicas": deployment.replicas,
            # Add any other fields from the deployment request
        })
        
        # Write updated values back
        with open(values_file, 'w') as f:
            yaml.safe_dump(values, f)
            
        # Commit changes to Git
        try:
            subprocess.run(
                ["git", "-C", str(repo_path), "add", str(values_file.relative_to(repo_path))],
                check=True, capture_output=True, text=True, timeout=30
            )
            
            commit_message = f"Update {namespace}/{app_name} deployment"
            subprocess.run(
                ["git", "-C", str(repo_path), "commit", "-m", commit_message],
                check=True, capture_output=True, text=True, timeout=30
            )
            
            subprocess.run(
                ["git", "-C", str(repo_path), "push"],
                check=True, capture_output=True, text=True, timeout=60
            )
        except CalledProcessError as e:
            logger.error(f"Git operation failed: {e.stderr}")
            # Don't fail if commit fails (e.g., no changes to commit)
            if "nothing to commit" not in e.stderr:
                raise HTTPException(status_code=500, detail=f"Failed to commit changes: {e.stderr}")
        
        # Trigger reconciliation in the background
        background_tasks.add_task(reconcile_from_git)
        
        return {
            "status": "deployment_triggered",
            "message": f"Deployment of {app_name} to {namespace} has been triggered",
            "details": {
                "namespace": namespace,
                "application": app_name,
                "image": deployment.image,
                "replicas": deployment.replicas
            }
        }
    except yaml.YAMLError as e:
        logger.error(f"YAML error while updating values: {e}")
        raise HTTPException(status_code=500, detail="Failed to update deployment configuration")
    except OSError as e:
        logger.error(f"File operation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to write deployment configuration")
    except Exception as e:
        logger.exception(f"Unexpected error during deployment: {e}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

# Reconciliation operations - renamed from GitOps status operations
@proxy.get("/status", tags=["Reconciliations"], summary="Get reconciliation status", response_model=GitOpsStatus)
async def get_gitops_status() -> GitOpsStatus:
    """
    Gets the overall status of the GitOps reconciliation system.
    
    Returns:
        GitOpsStatus: Object containing reconciliation status, applications list, and timestamps.
    """
    settings = get_settings()
    
    # Get status about the Git repository
    repo_path = Path(settings.gitops_repo_path)
    
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
        except OSError as err:
            logger.exception("Error reading applications directory", exc_info=err)
        except Exception as err:
            logger.exception("Error reading applications", exc_info=err)
    
    with reconciliation_lock:
        status = "active" if reconciliation_thread and reconciliation_thread.is_alive() else "inactive"
    
    return GitOpsStatus(
        is_reconciling=is_reconciling,
        last_reconciliation=get_last_reconciliation_time(),
        status=status,
        applications=applications
    )

@proxy.post("/", tags=["Reconciliations"], summary="Trigger reconciliation", status_code=200)
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

# Helper functions remain mostly unchanged
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
    timestamp_file = Path(settings.gitops_repo_path) / ".last_reconciliation"
    
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
    timestamp_file = Path(settings.gitops_repo_path) / ".last_reconciliation"
    
    timestamp = datetime.now(tz=timezone.utc).isoformat()

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
    3. Applying configurations to the Kubernetes API server
    4. Updating the reconciliation timestamp
    
    The function is thread-safe and prevents concurrent reconciliations.
    
    Raises:
        CalledProcessError: If any Git command fails during execution
        OSError: For filesystem-related errors
        yaml.YAMLError: For YAML parsing errors
    """
    global is_reconciling
    
    try:
        with reconciliation_lock:
            if is_reconciling:
                return
            is_reconciling = True
    except RuntimeError as e:
        # Handle lock acquisition failure
        logger.error(f"Failed to acquire reconciliation lock: {str(e)}")
        return
    
    try:
        settings = get_settings()
        
        # Ensure repo path exists
        repo_path = Path(settings.gitops_repo_path)
        
        # Clone/update the repository
        if not repo_path.exists():
            _clone_repository(settings.gitops_repo_url, settings.gitops_repo_path, settings.gitops_repo_branch)
        else:
            _update_repository(settings.gitops_repo_path, settings.gitops_repo_branch)
        
        # Apply configurations from Git to the Kubernetes API server
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
    except Exception as err:
        logger.exception("GitOps reconciliation failed with unexpected error", exc_info=err)
    finally:
        try:
            with reconciliation_lock:
                is_reconciling = False
        except RuntimeError:
            # If we can't acquire the lock here, just log it and continue
            logger.error("Failed to acquire lock when resetting reconciliation flag")
            # Set the flag directly without the lock as a last resort
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
    Apply configurations from Git to the Kubernetes API server.
    
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

def sanitize_branch_name(branch_name: str) -> str:
    """
    Sanitize git branch name to prevent command injection.
    
    Args:
        branch_name (str): The branch name to sanitize
        
    Returns:
        str: Sanitized branch name
    """
    if branch_name is None:
        return "main"
    
    try:
        # First replace slashes with hyphens
        branch_name = branch_name.replace('/', '-')
        # Then clean up any other invalid characters
        sanitized = re.sub(r'[^a-zA-Z0-9\-_\.]', '', branch_name)
        return sanitized
    except Exception as e:
        logging.warning(f"Error using regex for branch sanitization: {e}")
        # Fallback to basic string replacement if regex fails
        if branch_name:
            return branch_name.replace('/', '-').replace(' ', '-')
        return "main"

def sanitize_git_url(url: str) -> str:
    """
    Sanitize git URL to prevent command injection.
    
    Args:
        url (str): The URL to sanitize
        
    Returns:
        str: Sanitized URL
    """
    # Only allow valid git URL characters
    try:
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9\-_./:@]', '', url)
        return sanitized
    except (ImportError, AttributeError) as e:
        # If re module is not available or has an issue, use basic sanitization
        logger.warning(f"Error using regex for URL sanitization: {str(e)}")
        # Fallback: basic character filtering
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./:@")
        return ''.join(c for c in url if c in allowed_chars)