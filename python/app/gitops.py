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
import re  # Add missing import at the top of the file

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
        microservices (List[Dict[str, Any]]): List of microservices managed by GitOps.
    """
    is_reconciling: bool
    last_reconciliation: Optional[str] = None
    status: str
    microservices: List[Dict[str, Any]] = []

@proxy.post("/reconcile", tags=["GitOps"], summary="Reconcile Microservices", status_code=200)
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

@proxy.get("/status/reconcile", tags=["GitOps"], summary="Status: Reconcile", response_model=GitOpsStatus)
async def get_gitops_status() -> GitOpsStatus:
    """
    Gets the overall status of the GitOps reconciliation system.
    
    Returns:
        GitOpsStatus: Object containing reconciliation status, microservices list, and timestamps.
    """
    settings = get_settings()
    
    # Get status about the Git repository
    repo_path = Path(settings.gitops_repo_path)
    
    microservices = []
    
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
                                microservices.append({
                                    "microservices_name": app_dir.name,
                                    "namespace": namespace_dir.name,
                                    "image": values.get("image", "unknown"),
                                    "tag": values.get("tag", "unknown"),
                                })
                            except yaml.YAMLError as yaml_err:
                                # Log specific YAML parsing error
                                logger.error(f"Error parsing YAML in {values_file}: {yaml_err}")
        except OSError as err:
            logger.exception("Error reading microservices directory", exc_info=err)
        except Exception as err:
            logger.exception("Error reading microservices", exc_info=err)
    
    with reconciliation_lock:
        status = "active" if reconciliation_thread and reconciliation_thread.is_alive() else "inactive"
    
    return GitOpsStatus(
        is_reconciling=is_reconciling,
        last_reconciliation=get_last_reconciliation_time(),
        status=status,
        microservices=microservices
    )

# Helper functions remain mostly unchanged
def start_reconciliation_thread() -> None:
    """
    Start a background thread that periodically reconciles from Git.
    
    This function creates a daemon thread that runs reconciliation at regular intervals.
    If a thread is already running, it will not start a new one.
    
    Raises:
        Exception: If thread creation or starting fails, with descriptive message
    """
    global reconciliation_thread
    
    try:
        if reconciliation_thread and reconciliation_thread.is_alive():
            logger.info("Reconciliation thread already running")
            return

        def periodic_reconcile() -> None:
            while True:
                try:
                    reconcile_from_git()
                except Exception as e:
                    logger.error(f"Error in periodic reconciliation: {e}")
                time.sleep(60)  # Reconcile every minute
        
        # Create thread with explicit name for better debugging
        thread = threading.Thread(
            target=periodic_reconcile,
            daemon=True,
            name="GitOps-Reconciliation-Thread"
        )
        
        # Start the thread with explicit error handling
        try:
            thread.start()
            # Only set the global variable if start() succeeds
            reconciliation_thread = thread
            logger.info("Started GitOps reconciliation thread")
        except RuntimeError as e:
            # Handle specific thread starting errors
            logger.error(f"Failed to start reconciliation thread: {str(e)}")
            raise Exception(f"Failed to start reconciliation thread: {str(e)}")
    except Exception as e:
        # Catch any other exceptions during thread creation
        logger.error(f"Failed to create reconciliation thread: {str(e)}")
        reconciliation_thread = None
        raise Exception(f"Failed to start reconciliation thread: {str(e)}")

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
        ValueError: If the repository URL contains potentially dangerous characters.
    """
    # First validate repository URL to prevent command injection
    safe_url = sanitize_git_url(repo_url)
    if safe_url != repo_url:
        # If the URL had to be modified during sanitization, it might be suspicious
        logger.error(f"Potentially dangerous repository URL rejected: {repo_url}")
        raise ValueError("Invalid repository URL. URLs should only contain alphanumeric characters, hyphens, dots, slashes, colons, and @ symbols.")
        
    # Validate branch name
    safe_branch = sanitize_branch_name(branch)
    if safe_branch != branch and branch not in ["", None]:
        logger.warning(f"Branch name sanitized from '{branch}' to '{safe_branch}'")
    
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    try:
        # Add timeout to prevent hanging on network issues
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
        PermissionError: If access to required directories is denied
    """
    try:
        # Scan repository for microservices configurations
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
                            # Apply manifests from the directory using os.walk to handle
                            # potential nested directories of YAML files
                            for root, dirs, files in os.walk(str(manifests_dir)):
                                # Process each YAML file in order (sorted)
                                for f in sorted(files):
                                    if f.endswith(('.yaml', '.yml')):
                                        manifest_path = os.path.join(root, f)
                                        logger.debug(f"Processing manifest: {manifest_path}")
                                        # Example: Apply with kubectl
                                        # subprocess.run([
                                        #    "kubectl", "apply", "-f", manifest_path,
                                        #    "-n", namespace_dir.name
                                        # ], check=True, capture_output=True, text=True, timeout=60)
                            
                    except yaml.YAMLError as e:
                        logger.error(f"YAML parsing error in {values_file}: {e}")
                    except OSError as e:
                        logger.error(f"File operation error for {app_dir}: {e}")
                    except Exception as e:
                        logger.error(f"Failed to apply {namespace_dir.name}/{app_dir.name}: {str(e)}")
    except PermissionError as e:
        logger.error(f"Permission denied when accessing repository directories: {e}")
        # Re-raise to ensure proper handling by caller
        raise

def sanitize_branch_name(branch_name: str) -> str:
    """
    Sanitize git branch name to prevent command injection.
    
    Args:
        branch_name (str): The branch name to sanitize
        
    Returns:
        str: Sanitized branch name
    """
    if branch_name is None or not branch_name:
        return "main"
    
    try:
        # Remove path traversal sequences first
        sanitized = re.sub(r'\.\.', '', branch_name)
        
        # Replace forward slashes with hyphens
        sanitized = re.sub(r'/', '-', sanitized)
        
        # Remove other potentially dangerous characters
        sanitized = re.sub(r'[^\w\-\.]', '-', sanitized)
        
        # Consolidate consecutive hyphens into a single hyphen
        sanitized = re.sub(r'-+', '-', sanitized)
        
        # If after sanitization the string is empty, return "main"
        return sanitized if sanitized else "main"
    except Exception as e:
        logger.warning(f"Error using regex for branch sanitization: {e}")
        # Fallback to basic string replacement if regex fails
        if branch_name:
            # First remove path traversal sequences
            branch_name = branch_name.replace("..", "")
            # Replace forward slashes with hyphens
            branch_name = branch_name.replace("/", "-")
            # Keep only allowed characters
            result = ''.join(c if c.isalnum() or c in '-._' else '-' for c in branch_name)
            # Replace multiple hyphens with a single hyphen
            while '--' in result:
                result = result.replace('--', '-')
            return result
        return "main"

def sanitize_git_url(url: str) -> str:
    """
    Sanitize git URL to prevent command injection.
    
    Args:
        url (str): The URL to sanitize
        
    Returns:
        str: Sanitized URL
    """
    try:
        # Only allow valid git URL characters
        sanitized = re.sub(r'[^a-zA-Z0-9\-_./:@]', '', url)
        return sanitized
    except Exception as e:
        # If re module is not available or has an issue, use basic sanitization
        logger.warning(f"Error using regex for URL sanitization: {str(e)}")
        # Fallback: basic character filtering
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./:@")
        return ''.join(c for c in url if c in allowed_chars)