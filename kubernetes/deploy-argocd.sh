#!/bin/bash
# Deploy Argo CD to K3s cluster
set -e

# Ensure kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "kubectl not found, please install kubectl or ensure K3s is installed"
    exit 1
fi

echo "Deploying Argo CD using kustomize..."
kubectl apply -k $(dirname "$0")/argocd

echo "Waiting for Argo CD to be ready..."
kubectl -n argo-cd wait --for=condition=available deployment/argocd-server --timeout=5m

# Get the Argo CD server URL
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
ARGOCD_PORT=$(kubectl -n argo-cd get svc argocd-server -o jsonpath='{.spec.ports[0].nodePort}')

if [ -z "$ARGOCD_PORT" ]; then
  echo "Making Argo CD server accessible via NodePort..."
  kubectl patch svc argocd-server -n argo-cd -p '{"spec": {"type": "NodePort", "ports": [{"port": 80, "targetPort": 8080, "nodePort": 30081}]}}'
  ARGOCD_PORT=30081
fi

echo ""
echo "Argo CD has been deployed successfully! 🚀"
echo ""
echo "Access Argo CD UI at: http://$NODE_IP:$ARGOCD_PORT"
echo "Username: admin"
echo "Password: password"
echo ""
echo "To login via CLI:"
echo "argocd login $NODE_IP:$ARGOCD_PORT --username admin --password password --insecure"