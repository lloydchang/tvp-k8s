#!/bin/bash
# Script to test the TVP API endpoints

BASE_URL="http://localhost:8080"

echo "=== Testing TVP API Endpoints ==="

echo -e "\n1. Testing Root Endpoint (GET /)"
curl -s $BASE_URL/ | python3 -m json.tool || echo "Failed to connect"

echo -e "\n2. Testing Health Endpoint (GET /health)"
curl -s $BASE_URL/health | python3 -m json.tool || echo "Failed to connect"

echo -e "\n3. Testing Kubernetes Endpoint (GET /kubernetes/api/v1/namespaces)"
curl -s $BASE_URL/kubernetes/api/v1/namespaces | python3 -m json.tool || echo "Failed to connect"

echo -e "\n4. Testing Argo CD Endpoint (GET /argo/cd/applications)"
curl -s $BASE_URL/argo/cd/applications | python3 -m json.tool || echo "Failed to connect"

echo -e "\n5. Testing GitOps Status Endpoint (GET /gitops/status)"
curl -s $BASE_URL/gitops/status | python3 -m json.tool || echo "Failed to connect"

echo -e "\n=== Testing Complete ==="
