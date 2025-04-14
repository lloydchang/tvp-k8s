#!/bin/bash
# Script to set up a proper development environment for Kubernetes

# Color formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Setting up Kubernetes Development Environment ===${NC}"

# Check if we're running as root
if [ "$(id -u)" -eq 0; then
    echo -e "${YELLOW}Running as root. Will use k3s for local Kubernetes...${NC}"
    USE_K3S=true
else
    echo -e "${GREEN}Running as non-root. Will attempt to use minikube...${NC}"
    USE_K3S=false
fi

# Kill any existing processes
echo "Stopping any existing services..."
pkill -f "kubectl proxy" || true
pkill -f "k3s" || true

# Install necessary packages
echo "Checking for required packages..."
if ! command -v curl &> /dev/null; then
    echo "Installing curl..."
    apt-get update && apt-get install -y curl
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}kubectl is not installed. Please install kubectl first.${NC}"
    exit 1
fi

# Set up Kubernetes based on user context
if [ "$USE_K3S" = true ]; then
    echo "Setting up k3s lightweight Kubernetes..."
    
    # Check if k3s is already installed
    if ! command -v k3s &> /dev/null; then
        echo "Installing k3s..."
        curl -sfL https://get.k3s.io | sh -
        sleep 5
    fi
    
    # Configure kubectl to use k3s
    mkdir -p ~/.kube
    k3s kubectl config view --raw > ~/.kube/config
    chmod 600 ~/.kube/config
    export KUBECONFIG=~/.kube/config
    
    echo "Starting k3s server..."
    k3s server --disable-agent &
    K3S_PID=$!
    
    # Wait for k3s to be ready
    echo "Waiting for k3s to be ready..."
    sleep 10
else
    # Try using minikube
    echo "Setting up minikube..."
    
    if ! command -v minikube &> /dev/null; then
        echo -e "${RED}minikube is not installed. Please install minikube first.${NC}"
        exit 1
    fi
    
    echo "Starting minikube with docker driver..."
    minikube start --driver=docker
    
    # Wait for minikube to be ready
    echo "Waiting for minikube to be ready..."
    minikube status
fi

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

# Set proper environment variables
export KUBERNETES_API_URL="http://localhost:8001"
export ENVIRONMENT="development"
export VERIFY_SSL="false"

# Run the API service
echo -e "${GREEN}Starting the TVP API service...${NC}"
echo "API will be available at: http://localhost:8080"

# Navigate to the python directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv"; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install requirements
pip install -q -r ../requirements.txt

# Start the API
echo -e "${GREEN}Running API server...${NC}"
PYTHONPATH="$(pwd)/.." uvicorn api.index:app --host 0.0.0.0 --port 8080 --reload

# Clean up when the API server exits
echo "Cleaning up..."
if [ "$USE_K3S" = true ] && [ -n "$K3S_PID"; then
    kill "$K3S_PID" 2>/dev/null || true
fi
kill "$KUBECTL_PID" 2>/dev/null || true