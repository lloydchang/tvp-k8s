# app.py - Thin API layer for Kubernetes with FastAPI

from fastapi import FastAPI, HTTPException
from kubernetes import client, config

app = FastAPI()

# Load kubeconfig (adjust for in-cluster deployment)
# Load appropriate Kubernetes config based on environment
try:
    # Try to load in-cluster config first (when running inside a pod)
    config.load_incluster_config()
except config.ConfigException:
    # Fall back to local kubeconfig for development
    config.load_kube_config()

@app.post("/deploy")
async def deploy_app(name: str, image: str, replicas: int = 1):
    """
    Deploys an application to a Kubernetes cluster.
    
    Creates a Kubernetes deployment in the default namespace using the specified
    name, container image, and replica count. The deployment’s metadata and pod
    template labels are set based on the application name. Returns a success
    message on creation or raises an HTTPException (status code 500) if an error
    occurs.
    
    Parameters:
        name (str): Identifier for the deployment and pod labels.
        image (str): Container image to deploy.
        replicas (int, optional): Number of replicas to deploy. Defaults to 1.
    
    Returns:
        dict: A confirmation message indicating successful deployment.
    """
    v1 = client.AppsV1Api()

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=name),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(
                match_labels={"app": name},
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": name},
                ),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name=name, image=image, ports=[
                        client.V1ContainerPort(container_port=80),
                    ])],
                )
            ),
        )
    )

    try:
        v1.create_namespaced_deployment(namespace="default", body=deployment)
        return {"message": f"Deployment {name} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

