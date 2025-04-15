#!/bin/bash
# Script to set up Kind Kubernetes and Argo CD in a dev container

set -e  # Exit on any error

# Color formatting for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Setting up Kind Kubernetes and installing Argo CD ===${NC}"

# 1. Verify prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"
MISSING_TOOLS=""

# Check for curl
if ! command -v curl &> /dev/null; then
    echo "Installing curl..."
    apt-get update && apt-get install -y curl
fi

# Check for kubectl
if ! command -v kubectl &> /dev/null; then
    MISSING_TOOLS="${MISSING_TOOLS} kubectl"
else
    echo "✓ kubectl is installed"
fi

# Check for kind
if ! command -v kind &> /dev/null; then
    echo "Kind not found. Installing Kind..."
    curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
    chmod +x ./kind
    sudo mv ./kind /usr/local/bin/kind
    echo "✓ Kind installed"
else
    echo "✓ Kind is already installed"
fi

# Check for docker
if ! command -v docker &> /dev/null; then
    MISSING_TOOLS="${MISSING_TOOLS} docker"
else
    echo "✓ Docker is installed"
fi

# Exit if any required tools are missing
if [ ! -z "$MISSING_TOOLS" ]; then
    echo -e "${RED}Error: Missing required tools:${MISSING_TOOLS}${NC}"
    echo "Please install these tools and try again."
    exit 1
fi

# 2. Set up Kind Kubernetes cluster
echo -e "\n${YELLOW}Setting up Kind Kubernetes cluster...${NC}"

# Kill any existing processes
echo "Stopping any existing services..."
pkill -f "kubectl proxy" || true
pkill -f "kubectl port-forward" || true

# First, delete any existing kind clusters
kind delete cluster --name tvp-cluster 2>/dev/null || true

# Create a new Kind cluster
cat > kind-config.yaml << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: tvp-cluster
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
  - containerPort: 30080
    hostPort: 30080
    protocol: TCP
  - containerPort: 30443
    hostPort: 30443
    protocol: TCP
EOF

echo "Creating Kind cluster 'tvp-cluster'..."
kind create cluster --config kind-config.yaml

# Configure kubectl to use the correct context
echo "Configuring kubectl to use Kind cluster..."
kubectl config use-context kind-tvp-cluster

# Start kubectl proxy for API access
echo "Starting kubectl proxy on port 8001..."
kubectl proxy --address='0.0.0.0' --port=8001 --accept-hosts='.*' &
KUBECTL_PID=$!
echo "kubectl proxy started with PID: $KUBECTL_PID"

# Wait for kubectl proxy to be ready
echo "Checking if kubectl proxy is working..."
MAX_RETRIES=10
RETRY_COUNT=0
PROXY_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$PROXY_READY" = false ]; do
    if ps -p $KUBECTL_PID > /dev/null; then
        if curl -s http://localhost:8001/api/ > /dev/null 2>&1; then
            PROXY_READY=true
            echo -e "${GREEN}✓ kubectl proxy is working properly${NC}"
        else
            echo "Waiting for proxy to respond (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)..."
            sleep 3
            RETRY_COUNT=$((RETRY_COUNT+1))
        fi
    else
        echo "kubectl proxy process died. Restarting..."
        kubectl proxy --address='0.0.0.0' --port=8001 --accept-hosts='.*' &
        KUBECTL_PID=$!
        sleep 3
        RETRY_COUNT=$((RETRY_COUNT+1))
    fi
done

if [ "$PROXY_READY" = false ]; then
    echo -e "${RED}Failed to start kubectl proxy after multiple attempts.${NC}"
    echo "Continuing anyway, but Kubernetes API access may not work correctly."
fi

# 3. Verify Kubernetes cluster is running
echo -e "\n${YELLOW}Verifying Kubernetes cluster is running...${NC}"
kubectl get nodes
kubectl cluster-info

# 4. Install Argo CD
echo -e "\n${YELLOW}Installing Argo CD...${NC}"

# Create namespace
kubectl create namespace argocd

# Apply Argo CD installation manifests
echo "Applying Argo CD manifests..."
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "Waiting for Argo CD pods to be ready..."
echo "This may take a few minutes..."
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# 5. Configure Argo CD access
echo -e "\n${YELLOW}Configuring Argo CD access...${NC}"

# Patch the argocd-server service to use NodePort for access
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort", "ports": [{"name": "http", "port": 80, "targetPort": 8080, "nodePort": 30080}, {"name": "https", "port": 443, "targetPort": 8080, "nodePort": 30443}]}}'

# Get the initial admin password
echo -e "\n${YELLOW}Retrieving Argo CD admin password...${NC}"
ARGO_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo -e "Argo CD admin password: ${GREEN}${ARGO_PASSWORD}${NC}"

# 6. Set up port-forwarding for easier access (in background)
echo -e "\n${YELLOW}Setting up port-forwarding for Argo CD...${NC}"
echo "Starting port-forward for Argo CD API server on port 8080..."
pkill -f "kubectl port-forward.*argocd" || true
kubectl port-forward svc/argocd-server -n argocd 8080:80 > /dev/null 2>&1 &
PORT_FORWARD_PID=$!
echo "Port-forward started with PID: $PORT_FORWARD_PID"

# 7. Configure environment for TVP API
echo -e "\n${YELLOW}Configuring environment for TVP API...${NC}"

# Create a config file to store credentials
cat > ~/.tvp-k8s-config << EOF
# TVP Kubernetes and Argo CD configuration
export KUBERNETES_API_URL="http://localhost:8001"
export ARGO_CD_URL="http://localhost:8080"
export ARGO_CD_USERNAME="admin"
export ARGO_CD_PASSWORD="${ARGO_PASSWORD}"
export ENVIRONMENT="development"
export VERIFY_SSL="false"
EOF

# Source the config file
source ~/.tvp-k8s-config

echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo -e "Kind Kubernetes cluster 'tvp-cluster' is running"
echo -e "Argo CD URL: ${GREEN}http://localhost:8080${NC}"
echo -e "Argo CD username: ${GREEN}admin${NC}"
echo -e "Argo CD password: ${GREEN}${ARGO_PASSWORD}${NC}"
echo -e "Kubernetes API URL: ${GREEN}http://localhost:8001${NC}"
echo -e "\nYou can now use the TVP API with real Kubernetes and Argo CD services!"
echo -e "Run your API with: ${YELLOW}source ~/.tvp-k8s-config && cd /workspaces/tvp/python && ./run-api.sh${NC}"
echo -e "\nTo clean up this setup, use: ${YELLOW}pkill -f 'kubectl proxy'; pkill -f 'kubectl port-forward'; kind delete cluster --name tvp-cluster${NC}"

# Trap to clean up when the script exits
trap cleanup EXIT

function cleanup() {
    echo "Cleaning up..."
    kill "$KUBECTL_PID" 2>/dev/null || true
    kill "$PORT_FORWARD_PID" 2>/dev/null || true
}
