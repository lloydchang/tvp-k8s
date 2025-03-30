from fastapi import FastAPI, Depends, HTTPException, Request
from kubernetes import client, config
from kubernetes.client.rest import ApiException

app = FastAPI()

def get_k8s_client():
    """
    Loads Kubernetes configuration and returns a Kubernetes API client.
    
    This function loads the kubeconfig file using the Kubernetes client library and instantiates an
    ApiClient for interacting with a Kubernetes cluster.
    """
    config.load_kube_config()
    return client.ApiClient()

@app.api_route("/k8s-passthru/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def kubernetes_passthru(
    path: str,
    request: Request,
    k8s_client: client.ApiClient = Depends(get_k8s_client)
):
    """
    Forward a request to the Kubernetes API.
    
    This asynchronous endpoint forwards client requests to the Kubernetes API. It conditionally
    extracts the request body based on the HTTP method, constructs the corresponding Kubernetes
    API URL using the provided path, and streams the Kubernetes API response back to the client.
    A placeholder is included for implementing authentication and authorization logic.
    
    Raises:
        HTTPException: If the Kubernetes API call fails or an internal error occurs.
    
    Returns:
        The raw content of the Kubernetes API response.
    """

    # Authentication/Authorization (CRITICAL!) - Replace with your auth logic
    # Check user permissions, e.g., using RBAC or other authentication mechanism
    # Example:  if not has_permission(user, "k8s:" + path, request.method):
    #              raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
        headers = request.headers
        method = request.method

        # Construct the Kubernetes API URL
        k8s_url = f"/api/v1/{path}"  # Adjust for API group/version as needed

        response = k8s_client.call_api(
            k8s_url,
            method=method,
            body=body,
            header_params=headers,
            response_type=object,  # Generic response type
            _preload_content=False  # Stream response directly
        )

        # Handle the Kubernetes API response and return it to the client
        return await response.read()  # Read response content

    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=f"Kubernetes API error: {e.reason}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")