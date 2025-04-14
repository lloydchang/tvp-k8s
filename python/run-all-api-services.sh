#!/bin/bash
# Script to run Kubernetes proxy and FastAPI server with proper configuration

echo "=== Setting up environment and required services ==="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl could not be found"
    exit 1
fi

# Kill any existing kubectl proxy processes
echo "Stopping any existing kubectl proxy processes..."
pkill -f "kubectl proxy" || echo "No kubectl proxy processes found"
# Clean up zombie processes
echo "Cleaning up any zombie kubectl processes..."
ps -ef | grep defunct | grep kubectl | awk '{print $2}' | xargs -r kill -9

# Install curl if not available
if ! command -v curl &> /dev/null; then
    echo "Installing curl..."
    apt-get update && apt-get install -y curl
fi

# Start kubectl proxy on port 8001
echo "Starting kubectl proxy on port 8001..."
kubectl proxy --address='0.0.0.0' --port=8001 --accept-hosts='.*' &
KUBECTL_PID=$!
echo "kubectl proxy started with PID: $KUBECTL_PID"

# Make sure kubectl proxy is running
echo "Waiting for kubectl proxy to start..."
MAX_RETRIES=10
RETRY_COUNT=0
PROXY_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$PROXY_READY" = false ]; do
    if ps -p $KUBECTL_PID > /dev/null 2>&1; then
        # Process is still running, check if it's responding
        if curl -s http://localhost:8001/api/ > /dev/null 2>&1; then
            PROXY_READY=true
            echo "✓ kubectl proxy is working properly"
        else
            echo "Attempt $((RETRY_COUNT+1))/$MAX_RETRIES: Waiting for proxy to respond..."
            sleep 2
            RETRY_COUNT=$((RETRY_COUNT+1))
        fi
    else
        echo "kubectl proxy process died. Restarting..."
        kubectl proxy --address='0.0.0.0' --port=8001 --accept-hosts='.*' &
        KUBECTL_PID=$!
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT+1))
    fi
done

if [ "$PROXY_READY" = false ]; then
    echo "WARNING: kubectl proxy is not responding after multiple attempts."
    echo "Kubernetes API access may not work correctly, but continuing anyway."
    echo "Check your Kubernetes configuration with 'kubectl cluster-info'"
fi

# Kill any existing uvicorn processes
echo "Stopping any existing uvicorn processes..."
pkill -f "uvicorn" || echo "No uvicorn processes found"

# Set environment variables for API server
export KUBERNETES_API_URL="http://localhost:8001"
export VERIFY_SSL="false"
export PYTHONPATH="$(pwd)/.."

# Create a proxy-specific kubeconfig for better reliability
echo "Creating proxy-specific kubeconfig..."
mkdir -p ~/.kube
cat > ~/.kube/proxy-config << EOF
apiVersion: v1
clusters:
- cluster:
    server: http://localhost:8001
  name: proxy-cluster
contexts:
- context:
    cluster: proxy-cluster
    user: proxy-user
  name: proxy-context
current-context: proxy-context
kind: Config
preferences: {}
users:
- name: proxy-user
  user: {}
EOF

export KUBECONFIG=~/.kube/proxy-config
echo "✓ Custom kubeconfig created at: ~/.kube/proxy-config"

# Navigate to the python directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install required packages
echo "Installing required packages..."
pip install -q -r ../requirements.txt

# Print debugging information
echo "Current environment configuration:"
echo "KUBERNETES_API_URL: $KUBERNETES_API_URL"
echo "KUBECONFIG: $KUBECONFIG"
echo "VERIFY_SSL: $VERIFY_SSL"
echo "PYTHONPATH: $PYTHONPATH"

# Start the FastAPI server
echo "Starting FastAPI server on port 8080..."
echo "API will be available at: http://localhost:8080"
echo "Health check will be available at: http://localhost:8080/health"
echo "Kubernetes endpoints will be available at: http://localhost:8080/kubernetes/api/v1/..."
echo "---"
echo "Press Ctrl+C to stop all services"

# Run the API server with debug logging enabled
PYTHONPATH=$PYTHONPATH uvicorn api.index:app --host 0.0.0.0 --port 8080 --reload --log-level debug

# When uvicorn is stopped, also stop kubectl proxy
echo "Stopping kubectl proxy..."
kill $KUBECTL_PID
