#!/bin/bash
# Script to set up a proper development environment for Kubernetes using Kind

# Color formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Setting up Kind Kubernetes Development Environment ===${NC}"

# Kill any existing processes
echo "Stopping any existing services..."
pkill -f "kubectl proxy" || true

# Install necessary packages
echo "Checking for required packages..."
if ! command -v curl &> /dev/null; then
    echo "Installing curl..."
    apt-get update && apt-get install -y curl
fi

# Check for kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}kubectl is not installed. Please install kubectl first.${NC}"
    exit 1
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
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

echo "Setting up Kind Kubernetes cluster..."

# Delete any existing kind clusters
kind delete cluster --name dev-cluster 2>/dev/null || true

# Create a new Kind cluster
cat > kind-config.yaml << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: dev-cluster
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

echo "Creating Kind cluster 'dev-cluster'..."
kind create cluster --config kind-config.yaml

# Configure kubectl to use the correct context
echo "Configuring kubectl to use Kind cluster..."
kubectl config use-context kind-dev-cluster

# Start kubectl proxy
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

# Verify the Kind cluster is running
echo -e "\n${YELLOW}Verifying Kubernetes cluster is running...${NC}"
kubectl get nodes
kubectl cluster-info

echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo -e "Kind Kubernetes cluster is running"
echo -e "Kubernetes API URL: ${GREEN}http://localhost:8001${NC}"
echo -e "\nTo access the Kubernetes Dashboard, run:"
echo -e "${YELLOW}kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml${NC}"
echo -e "${YELLOW}kubectl proxy${NC}"
echo -e "Then visit: ${GREEN}http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/${NC}"
echo -e "\nTo clean up this setup, use: ${YELLOW}pkill -f 'kubectl proxy'; kind delete cluster --name dev-cluster${NC}"

# Clean up function
function cleanup() {
    echo "Cleaning up..."
    kill "$KUBECTL_PID" 2>/dev/null || true
}

# Register the cleanup function to run on script exit
trap cleanup EXIT
