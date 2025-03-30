from fastapi import FastAPI, Depends, HTTPException, status
from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException
import yaml

app = FastAPI()

def get_k8s_client():
    """
    Retrieves a Kubernetes API client.
    
    Loads the local Kubernetes configuration and returns a new ApiClient instance for interacting with the cluster.
    """
    config.load_kube_config()
    return client.ApiClient()

@app.post("/argocd/applications", status_code=status.HTTP_201_CREATED)
async def create_argocd_application(
    repo_url: str,
    path: str,
    target_namespace: str,
    app_name: str,
    k8s_client: client.ApiClient = Depends(get_k8s_client)
):
    """
    Creates an Argo CD Application.
    
    This asynchronous endpoint constructs a YAML manifest for an Argo CD Application using the provided repository URL, manifest path, target namespace, and application name, then applies it to a Kubernetes cluster. On success, it returns a confirmation message; if the creation fails, an HTTPException is raised with details from the Kubernetes API.
    
    Args:
        repo_url: URL of the Git repository containing the application's source.
        path: Relative path within the repository to the application's manifests.
        target_namespace: Kubernetes namespace where the application will be deployed.
        app_name: Name assigned to the Argo CD application.
    
    Returns:
        A dictionary with a success message confirming the application's creation.
    
    Raises:
        HTTPException: If an error occurs during application creation.
    """

    # Construct the Application YAML
    application_yaml = f"""
    apiVersion: argoproj.io/v1alpha1
    kind: Application
    metadata:
      name: {app_name}
      namespace: argocd
      finalizers:
      - resources-finalizer.argocd.argoproj.io
    spec:
      destination:
        namespace: {target_namespace}
        server: https://kubernetes.default.svc
      project: default # Replace with your AppProject if needed
      source:
        path: {path}
        repoURL: {repo_url}
        targetRevision: HEAD
        directory:
          recurse: true
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
        - CreateNamespace=true
    """

    try:
        k8s_client.configuration.assert_hostname = False # Security Warning: In production, verify TLS certificates!
        utils.create_from_yaml(k8s_client, yaml.safe_load_all(application_yaml))

        return {"message": f"Argo CD Application '{app_name}' created successfully."}

    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=f"Failed to create Argo CD Application: {e}")


@app.post("/argocd/applications/{app_name}/sync")
@app.post("/argocd/applications/{app_name}/sync")
async def sync_argocd_application(app_name: str) -> None:
    k8s_client = get_k8s_client()
    # Implementation for triggering sync
    pass
   #Implementation for triggering sync
   """
   Triggers synchronization of an Argo CD application.
   
   This asynchronous endpoint initiates the synchronization process for the Argo CD
   application identified by its name. The current implementation is a placeholder.
   
   Args:
       app_name: The name of the Argo CD application to be synchronized.
   """
   pass


# Example of how to get application status