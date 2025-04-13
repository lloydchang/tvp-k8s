#!/bin/bash
# Comprehensive script to set up and test the TVP API

echo "=== Setting up TVP API and testing endpoints ==="
echo "Setting up environment..."

# Kill any existing processes
pkill -f "kubectl proxy" || echo "No kubectl proxy processes to kill"
pkill -f "uvicorn" || echo "No uvicorn processes to kill"

# Set up kubectl proxy for Kubernetes API access
echo "Starting kubectl proxy on port 8001..."
kubectl proxy --address='0.0.0.0' --port=8001 --accept-hosts='.*' &
KUBECTL_PROXY_PID=$!
echo "kubectl proxy started with PID: $KUBECTL_PROXY_PID"

# Verify kubectl proxy is responding
echo "Verifying kubectl proxy is accessible..."
sleep 2
if curl -s http://localhost:8001/api/ > /dev/null; then
    echo "✓ kubectl proxy is working and responding at http://localhost:8001/api/"
else
    echo "✗ kubectl proxy is not responding. Stopping script."
    kill $KUBECTL_PROXY_PID
    exit 1
fi

# Set up environment variables for API server
export KUBERNETES_API_URL=http://localhost:8001
export VERIFY_SSL=false

echo "Starting FastAPI server..."
cd /app && export PYTHONPATH="${PYTHONPATH}:$(pwd)" && cd python && source venv/bin/activate && uvicorn api.index:app --host 0.0.0.0 --port 8080 &
API_PID=$!
echo "FastAPI server started with PID: $API_PID"

# Wait for API server to be ready
echo "Waiting for API server to start..."
sleep 5

# Test API endpoints
echo -e "\n=== Testing API Endpoints ==="
echo "Testing root endpoint (GET /):"
curl -s http://localhost:8080/

echo -e "\n\nTesting health endpoint (GET /health):"
curl -s http://localhost:8080/health

echo -e "\n\nTesting Kubernetes endpoint (GET /kubernetes/api/v1/namespaces):"
curl -s http://localhost:8080/kubernetes/api/v1/namespaces

echo -e "\n\nTesting Argo CD endpoint (GET /argo/cd/applications):"
curl -s http://localhost:8080/argo/cd/applications

echo -e "\n\nTesting GitOps status endpoint (GET /gitops/status):"
curl -s http://localhost:8080/gitops/status

echo -e "\n\n=== Setup and testing complete ==="
echo "API is running on http://localhost:8080"
echo "Health check is available at http://localhost:8080/health"
echo "Use $BROWSER http://localhost:8080 to open the API in your browser"
echo "Press Ctrl+C when finished to stop all services"

# Wait for user to press Ctrl+C
wait $API_PID
kill $KUBECTL_PROXY_PID
