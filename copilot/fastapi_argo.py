# fastapi_argo.py - FastAPI app that integrates with ArgoCD via GitOps

from fastapi import FastAPI, HTTPException
import subprocess
import os
from git import Repo

app = FastAPI()

# Git repository containing Kubernetes manifests for ArgoCD
GIT_REPO_URL = "git@github.com:your-org/k8s-apps.git"
GIT_REPO_PATH = "/tmp/k8s-apps"
GIT_BRANCH = "main"

def clone_or_pull_repo():
    """Clones the repo if it doesn't exist; otherwise, pulls the latest changes."""
    if os.path.exists(GIT_REPO_PATH):
        repo = Repo(GIT_REPO_PATH)
        repo.git.pull()
    else:
        Repo.clone_from(GIT_REPO_URL, GIT_REPO_PATH, branch=GIT_BRANCH)

def update_k8s_manifest(app_name, image, replicas):
    """
    Updates the Kubernetes deployment manifest for the specified application.
    
    Constructs a Kubernetes deployment configuration in YAML format using the provided
    application name, container image, and replica count. The resulting manifest is
    written to the deployment.yaml file located at the app's directory under the
    repository path, replacing any existing configuration.
    
    Parameters:
        app_name: The name of the application.
        image: The container image to use in the deployment.
        replicas: The desired number of replicas for the deployment.
    """
    file_path = f"{GIT_REPO_PATH}/apps/{app_name}/deployment.yaml"

    # Example of modifying a YAML file
    new_yaml = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: default
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
      - name: {app_name}
        image: {image}
        ports:
        - containerPort: 80
    """
    
    with open(file_path, "w") as f:
        f.write(new_yaml)

def commit_and_push_changes(app_name):
    """
    Commits repository changes and pushes them to the remote.
    
    Stages updated files, creates a commit with a message indicating the deployment update for the given
    application, and pushes the commit to the remote repository.
    
    Args:
        app_name: The name of the application whose deployment update is being committed.
    """
    try:
        repo = Repo(GIT_REPO_PATH)
        repo.git.add(update=True)
        repo.index.commit(f"Deploy {app_name} update via FastAPI")
        repo.remote(name="origin").push()
    except Exception as e:
        raise Exception(f"Git commit/push operation failed: {str(e)}") from e

@app.post("/deploy")
def deploy_application(app_name: str, image: str, replicas: int = 1):
    """
    Deploys an application by updating its Kubernetes deployment manifest.
    
    This function orchestrates the deployment process by ensuring the latest state of the Git repository
    is available, updating the Kubernetes manifest with the specified container image and replica count,
    and committing and pushing the changes to the remote repository. A confirmation message is returned
    upon success, prompting ArgoCD to synchronize the deployment. If any operation fails, an HTTPException
    with a 500 status code is raised.
    
    Args:
        app_name: The name of the application to deploy.
        image: The container image to use in the deployment.
        replicas: The number of replicas for the deployment (default is 1).
    
    Returns:
        A dictionary containing a message confirming the update.
    
    Raises:
        HTTPException: If an error occurs during repository operations or manifest updates.
    """
    try:
        clone_or_pull_repo()
        update_k8s_manifest(app_name, image, replicas)
        commit_and_push_changes(app_name)
        return {"message": f"Deployment for {app_name} updated. ArgoCD will sync automatically."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
