#!/bin/bash
# K3s Installation Script for TVP
set -e

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Install K3s
echo "Installing K3s..."
curl -sfL https://get.k3s.io | sh -

# Wait for K3s to be ready
echo "Waiting for K3s to start..."
until kubectl get node &>/dev/null; do
    echo "Waiting for K3s API..."
    sleep 5
done

echo "K3s is up and running!"

# Set up kubeconfig for non-root user
if [ ! -z "$SUDO_USER" ]; then
    USER_HOME=$(getent passwd $SUDO_USER | cut -d: -f6)
    mkdir -p $USER_HOME/.kube
    cp /etc/rancher/k3s/k3s.yaml $USER_HOME/.kube/config
    chown -R $SUDO_USER:$(id -gn $SUDO_USER) $USER_HOME/.kube
    export KUBECONFIG=$USER_HOME/.kube/config
    echo "Kubeconfig written to $USER_HOME/.kube/config"
fi

# Display cluster info
kubectl cluster-info
kubectl get nodes

echo ""
echo "K3s installation complete! 🚀"
echo "To use kubectl without sudo, run: export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
echo "Or use the copied config in your home directory"