#!/bin/bash
# Kubernetes Connection Diagnostics Script
# This script helps diagnose issues with Kubernetes connectivity in the TVP project

echo "=== Kubernetes Connection Diagnostics ==="
echo ""

# Check if k3s is installed and running
echo "Checking for K3s installation..."
if command -v k3s &> /dev/null; then
    echo "✅ K3s is installed"
    k3s_version=$(k3s --version)
    echo "   Version: $k3s_version"

    # Check for k3s processes
    k3s_processes=$(ps aux | grep k3s | grep -v grep)
    if [ -n "$k3s_processes" ]; then
        echo "✅ K3s processes are running:"
        echo "$k3s_processes"
    else
        echo "❌ No K3s processes found running"
    fi
else
    echo "❌ K3s is not installed"
fi

echo ""
echo "Checking kubeconfig setup..."

# Check if KUBECONFIG is set
if [ -n "$KUBECONFIG" ]; then
    echo "✅ KUBECONFIG environment variable is set to: $KUBECONFIG"
else
    echo "❌ KUBECONFIG environment variable is not set"
fi

# Check for existence of config file
default_kubeconfig="/app/.kube/config"
if [ -f "$default_kubeconfig" ]; then
    echo "✅ Kubeconfig file exists at: $default_kubeconfig"
    echo "   File permissions: $(ls -la $default_kubeconfig)"
    
    # Check kubeconfig content
    server_url=$(grep "server:" $default_kubeconfig | head -n1 | awk '{print $2}')
    if [ -n "$server_url" ]; then
        echo "   Server URL in config: $server_url"
    else
        echo "❌ No server URL found in kubeconfig"
    fi
else
    echo "❌ No kubeconfig file found at default location: $default_kubeconfig"
fi

echo ""
echo "Testing connectivity to Kubernetes API server..."

# Try different possible API server URLs
test_api_urls() {
    url="$1"
    echo "Testing connection to: $url"
    if curl -s -k "$url/version" &> /dev/null; then
        echo "✅ Connection successful to $url"
        echo "   API version info:"
        curl -s -k "$url/version" | grep -v "}\|{"
        return 0
    else
        echo "❌ Failed to connect to $url"
        return 1
    fi
}

# Try different possible endpoints
echo "Trying various API endpoints..."
test_api_urls "http://localhost:8080" || \
test_api_urls "https://localhost:6443" || \
test_api_urls "https://127.0.0.1:6443" || \
test_api_urls "http://127.0.0.1:8080" || \
echo "❌ Could not connect to any Kubernetes API endpoints"

echo ""
echo "Checking environment variables for TVP configuration..."
if [ -n "$KUBERNETES_API_URL" ]; then
    echo "✅ KUBERNETES_API_URL is set to: $KUBERNETES_API_URL"
    test_api_urls "$KUBERNETES_API_URL"
else
    echo "❌ KUBERNETES_API_URL environment variable is not set"
fi

echo ""
echo "Verifying port availability..."
netstat_available=false
ss_available=false

if command -v netstat &> /dev/null; then
    netstat_available=true
    echo "Checking ports with netstat:"
    netstat -tuln | grep -E '6443|8080'
elif command -v ss &> /dev/null; then
    ss_available=true
    echo "Checking ports with ss:"
    ss -tuln | grep -E '6443|8080'
else
    echo "❌ Neither netstat nor ss commands available to check ports"
fi

echo ""
echo "=== Recommendations ==="
echo "1. If K3s is not running, run: /app/kubernetes/k3s-setup.sh"
echo "2. Set environment variables for TVP:"
echo "   export KUBERNETES_API_URL=https://127.0.0.1:6443"
echo "   export KUBECONFIG=/app/.kube/config"
echo "   export VERIFY_SSL=false  # For development only"
echo "3. For a fallback approach, run kubectl proxy:"
echo "   kubectl proxy --address='0.0.0.0' --port=8001 --accept-hosts='.*' &"
echo "   export KUBERNETES_API_URL=http://localhost:8001"
echo ""
echo "Diagnostics complete."
