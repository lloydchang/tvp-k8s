#!/bin/bash
# Simple script to test TVP API endpoints

BASE_URL="http://localhost:8080"

echo "=== Testing Root Endpoint ==="
curl -s $BASE_URL || echo "Failed to connect"

echo -e "\n\n=== Testing Health Endpoint ==="
curl -s $BASE_URL/health || echo "Failed to connect"

echo -e "\n\n=== Testing Kubernetes Endpoint ==="
curl -s $BASE_URL/kubernetes/api/v1/namespaces || echo "Failed to connect"

echo -e "\n\n=== Testing Argo CD Endpoint ==="
curl -s $BASE_URL/argo/cd/applications || echo "Failed to connect"
