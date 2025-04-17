#!/bin/bash

set -euo pipefail

cd $(dirname $0)

BASE_DIR=$(pwd)

# Start port range for FastAPI
START_PORT=8000
MAX_PORT=65535  # Set to the maximum allowable port number

echo "Starting FastAPI server..."

# Find available port function
find_available_port() {
  local port=$START_PORT
  while [ $port -le $MAX_PORT ]; do
    if ! lsof -i:$port > /dev/null 2>&1; then
      echo $port
      return 0
    fi
    port=$((port+1))
  done
  echo "No available ports found"
  exit 1
}

# Check Kubernetes environment
check_kubernetes_env() {
  echo "Checking Kubernetes environment..."
  
  # Check if kubectl is available
  if command -v kubectl > /dev/null 2>&1; then
    echo "kubectl found, checking cluster connectivity..."
    if kubectl get nodes --request-timeout=3s > /dev/null 2>&1; then
      echo "✅ Successfully connected to Kubernetes server"
    else
      echo "⚠️ Cannot connect to Kubernetes server. In development mode, this is optional."
      
      # Check if we have kind clusters
      if command -v kind > /dev/null 2>&1; then
        CLUSTERS=$(kind get clusters 2>/dev/null || echo "")
        
        if [[ -n "$CLUSTERS" ]]; then
          echo "Kind clusters found: $CLUSTERS"
        else
          echo "No kind clusters found. You can create one with:"
          echo "  kind create cluster --name tvp-dev"
        fi
      else
        echo "Kind is not available. Kubernetes will be marked as degraded but the API will work."
      fi
    fi
  else
    echo "kubectl not found. Kubernetes will be marked as degraded but the API will work."
  fi
  
  echo "----------"
}

# Start kubectl proxy function
start_kubectl_proxy() {
  echo "Checking for existing kubectl proxy..."
  if pgrep -f "kubectl proxy" > /dev/null; then
    echo "kubectl proxy already running"
  else
    echo "Starting kubectl proxy on port 8001..."
    kubectl proxy --address='0.0.0.0' --port=8001 --accept-hosts='.*' &
    KUBECTL_PID=$!
    echo "kubectl proxy started with PID: $KUBECTL_PID"
    
    # Wait for proxy to be ready
    echo "Waiting for kubectl proxy to start..."
    MAX_RETRIES=5
    RETRY_COUNT=0
    PROXY_READY=false
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$PROXY_READY" = false ]; do
      if curl -s http://localhost:8001/api/ > /dev/null 2>&1; then
        PROXY_READY=true
        echo "✅ kubectl proxy is working properly"
      else
        echo "Waiting for proxy to respond (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)..."
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT+1))
      fi
    done
    
    if [ "$PROXY_READY" = false ]; then
      echo "⚠️ kubectl proxy is not responding. API will run but Kubernetes access may not work."
    fi
  fi
  
  # Export the Kubernetes API URL for the application to use
  export KUBERNETES_API_URL="http://localhost:8001"
  export ENVIRONMENT="development"
  export VERIFY_SSL="false"
}

# Get the first available port starting from START_PORT
AVAILABLE_PORT=$(find_available_port)
echo "Using available port: $AVAILABLE_PORT"

# Check Kubernetes environment 
check_kubernetes_env

# Start kubectl proxy
start_kubectl_proxy

# Activate virtual environment or create one
if [ -d "venv" ]; then
    echo 'Activating existing virtual environment...'
    source venv/bin/activate
else
    echo 'Creating virtual environment...'
    python -m venv venv
    source venv/bin/activate
fi

# Install runtime requirements
if [ -f "../requirements.txt" ]; then
    echo 'Installing runtime requirements...'
    pip install --upgrade pip
    pip install -r ../requirements.txt
else
    echo '../requirements.txt not found. Please ensure it exists.'
    exit 1
fi

# Explicitly install uvicorn if not already installed
if ! pip show uvicorn > /dev/null 2>&1; then
    echo 'Installing uvicorn...'
    pip install uvicorn
fi

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH:-$(pwd)/..}"
export PYTHONPATH="$BASE_DIR:$PYTHONPATH"

# Start Uvicorn server on the available port
echo "Running Uvicorn server on 0.0.0.0:$AVAILABLE_PORT..."
# Changed from api.index:app to app.index:app to match the actual directory structure
uvicorn app.index:app --host 0.0.0.0 --port $AVAILABLE_PORT --reload

# Manual run command for convenience
PYTHONPATH=/app KUBERNETES_API_URL=http://localhost:8001 ARGO_CD_URL=http://localhost:8080 ENVIRONMENT=development python -m uvicorn python.app.index:app --host 0.0.0.0 --port 8000
