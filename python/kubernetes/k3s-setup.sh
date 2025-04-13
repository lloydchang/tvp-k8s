#!/bin/bash
# K3s Setup Script for Docker Containers
# This script sets up K3s in a Docker container without requiring systemd

# Function to handle errors
handle_error() {
  echo "[ERROR] $1"
  exit 1
}

echo "Installing K3s for containerized environments..."

# Create necessary directories
mkdir -p /tmp/k3s /app/.kube

# Download K3s binary if it doesn't exist
if [ ! -f /usr/local/bin/k3s ]; then
  echo "Downloading K3s binary..."
  ARCH=$(uname -m)
  if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    ARCH_SUFFIX="arm64"
  else
    ARCH_SUFFIX="amd64"
  fi
  
  curl -Lo /usr/local/bin/k3s https://github.com/k3s-io/k3s/releases/download/v1.28.5+k3s1/k3s-$ARCH_SUFFIX || handle_error "Failed to download K3s binary"
  chmod +x /usr/local/bin/k3s || handle_error "Failed to make K3s executable"
fi

# Set up K3s configuration
mkdir -p /etc/rancher/k3s
cat > /etc/rancher/k3s/config.yaml << EOF
disable: 
  - traefik
  - servicelb
  - metrics-server
data-dir: /tmp/k3s
bind-address: 0.0.0.0
https-listen-port: 6443
kube-apiserver-arg: ["insecure-port=8080"]
write-kubeconfig: /app/.kube/config
write-kubeconfig-mode: 644
EOF

echo "Starting K3s server..."
# Run K3s without requiring systemd
K3S_TOKEN=tvpsecret k3s server --disable-agent &
PID=$!

# Wait for K3s to start
echo "Waiting for K3s to start (10 seconds)..."
sleep 10

# Check if K3s is running
if ps -p $PID > /dev/null; then
  echo "K3s started successfully with PID: $PID"
  # Setup kubectl configuration
  export KUBECONFIG=/app/.kube/config
  
  # Wait for API server to be ready
  echo "Waiting for Kubernetes API server to be ready..."
  SECONDS=0
  while ! k3s kubectl get nodes &>/dev/null; do
    if [ $SECONDS -gt 30 ]; then
      echo "Timed out waiting for API server. Check the logs at /tmp/k3s.log"
      break
    fi
    sleep 1
  done
  
  # Show node status
  echo "Kubernetes nodes:"
  k3s kubectl get nodes
  
  echo "Kubernetes is now available at: https://127.0.0.1:6443"
  echo "Kubeconfig is available at: /app/.kube/config"
else
  echo "Failed to start K3s. Check the logs at /tmp/k3s.log"
  exit 1
fi
