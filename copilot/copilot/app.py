# app.py - Thin API layer for Kubernetes with FastAPI

from fastapi import FastAPI, HTTPException
from kubernetes import client, config

app = FastAPI()

# Load kubeconfig (adjust for in-cluster deployment)
config.load_kube_config()

@app.post("/deploy")
async def deploy_app(name: str, image: str, replicas: int = 1):
    """
    Deploys a containerized application to Kubernetes.
    
    Creates a deployment in the "default" namespace with the specified name, container image, 
    and replica count. Returns a success message on successful creation; if an error occurs, 
    an HTTPException is raised with the error details.
    
    Args:
        name: The deployment name and pod label.
        image: The container image to deploy.
        replicas: The number of pod replicas to create (default is 1).
    
    Returns:
        A dictionary containing a success message.
    
    Raises:
        HTTPException: If an error occurs during deployment creation.
    """
    v1 = client.AppsV1Api()

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=name),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector={"matchLabels": {"app": name}},
            template=client.V1PodTemplateSpec(
                metadata={"labels": {"app": name}},
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name=name, image=image)]
                )
            ),
        )
    )

    try:
        v1.create_namespaced_deployment(namespace="default", body=deployment)
        return {"message": f"Deployment {name} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

