from fastapi import FastAPI, Depends, HTTPException, status
from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException
import yaml

app = FastAPI()

def get_k8s_client():
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
    """Creates an Argo CD Application."""

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
async def sync_argocd_application(app_name: str, k8s_client: client.ApiClient = Depends(get_k8s_client)):
   #Implementation for triggering sync
   pass


# Example of how to get application status