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
    """Updates the Kubernetes YAML file for the app."""
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
    """Commits and pushes the changes to Git."""
    repo = Repo(GIT_REPO_PATH)
    repo.git.add(update=True)
    repo.index.commit(f"Deploy {app_name} update via FastAPI")
    repo.remote(name="origin").push()

@app.post("/deploy")
def deploy_application(app_name: str, image: str, replicas: int = 1):
    try:
        clone_or_pull_repo()
        update_k8s_manifest(app_name, image, replicas)
        commit_and_push_changes(app_name)
        return {"message": f"Deployment for {app_name} updated. ArgoCD will sync automatically."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
