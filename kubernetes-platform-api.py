from fastapi import FastAPI, Depends
from kubernetes import client, config
from pydantic import BaseModel

app = FastAPI(title="Kubernetes Platform API")

# Kubernetes cluster connection
def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api()

class DeploymentRequest(BaseModel):
    name: str
    image: str
    replicas: int = 3
    namespace: str = "default"

@app.post("/deployments/")
async def create_deployment(
    deployment: DeploymentRequest, 
    k8s_api: client.CoreV1Api = Depends(get_k8s_client)
):
    # Implementation for creating a standardized deployment
    # Add custom logic, validation, and organizational standards
    deployment_spec = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=deployment.name),
        spec={
            "replicas": deployment.replicas,
            "template": {
                "spec": {
                    "containers": [{
                        "name": deployment.name,
                        "image": deployment.image
                    }]
                }
            }
        }
    )
    
    # Create deployment with organizational standards
    apps_v1 = client.AppsV1Api()
    response = apps_v1.create_namespaced_deployment(
        namespace=deployment.namespace, 
        body=deployment_spec
    )
    
    return {"status": "Deployment created", "details": response}

@app.get("/health")
async def health_check():
    return {"status": "Platform is healthy"}
