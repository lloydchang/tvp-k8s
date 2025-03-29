# app.py - Thin API layer for Kubernetes with FastAPI

from fastapi import FastAPI, HTTPException
from kubernetes import client, config

app = FastAPI()

# Load kubeconfig (adjust for in-cluster deployment)
config.load_kube_config()

@app.post("/deploy")
async def deploy_app(name: str, image: str, replicas: int = 1):
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

