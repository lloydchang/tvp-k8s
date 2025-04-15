#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import threading

class MockKubernetesHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()
        
    def do_GET(self):
        # Common mock response for Kubernetes API
        if self.path.startswith('/api/v1/namespaces'):
            response = {
                "kind": "NamespaceList",
                "apiVersion": "v1",
                "metadata": {
                    "resourceVersion": "12345"
                },
                "items": [
                    {
                        "metadata": {
                            "name": "default",
                            "uid": "12345-abcde",
                            "resourceVersion": "123",
                            "creationTimestamp": "2023-01-01T00:00:00Z"
                        },
                        "status": {
                            "phase": "Active"
                        }
                    },
                    {
                        "metadata": {
                            "name": "kube-system",
                            "uid": "67890-fghij",
                            "resourceVersion": "456",
                            "creationTimestamp": "2023-01-01T00:00:00Z"
                        },
                        "status": {
                            "phase": "Active"
                        }
                    },
                    {
                        "metadata": {
                            "name": "argocd",
                            "uid": "24680-klmno",
                            "resourceVersion": "789",
                            "creationTimestamp": "2023-01-01T00:00:00Z"
                        },
                        "status": {
                            "phase": "Active"
                        }
                    }
                ]
            }
            self._set_headers()
            self.wfile.write(json.dumps(response).encode())
            return
            
        elif self.path.startswith('/api/v1'):
            response = {
                "kind": "APIResourceList",
                "apiVersion": "v1",
                "groupVersion": "v1",
                "resources": [
                    {
                        "name": "namespaces",
                        "singularName": "namespace",
                        "namespaced": False,
                        "kind": "Namespace",
                        "verbs": ["create", "delete", "get", "list", "patch", "update", "watch"]
                    },
                    {
                        "name": "pods",
                        "singularName": "pod",
                        "namespaced": True,
                        "kind": "Pod",
                        "verbs": ["create", "delete", "get", "list", "patch", "update", "watch"]
                    }
                ]
            }
            self._set_headers()
            self.wfile.write(json.dumps(response).encode())
            return
            
        elif self.path == '/api':
            response = {
                "versions": ["v1"],
                "serverAddressByClientCIDRs": [
                    {
                        "clientCIDR": "0.0.0.0/0",
                        "serverAddress": "localhost:8001"
                    }
                ]
            }
            self._set_headers()
            self.wfile.write(json.dumps(response).encode())
            return
            
        # Default response
        self._set_headers()
        self.wfile.write(json.dumps({"message": "Mock Kubernetes API - Path: " + self.path}).encode())
    
    # Add support for POST, PUT, DELETE methods
    def do_POST(self):
        content_length = int(self.headers['Content-Length']) if 'Content-Length' in self.headers else 0
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            request_json = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            request_json = {}
            
        print(f"POST request to {self.path}")
        print(f"POST data: {request_json}")
        
        # Handle different POST endpoints
        if self.path.startswith('/api/v1/namespaces'):
            self._set_headers()
            response = {
                "kind": "Namespace",
                "apiVersion": "v1",
                "metadata": {
                    "name": request_json.get("metadata", {}).get("name", "new-namespace"),
                    "uid": "created-12345",
                    "resourceVersion": "999",
                    "creationTimestamp": "2023-01-01T00:00:00Z"
                },
                "status": {
                    "phase": "Active"
                }
            }
            self.wfile.write(json.dumps(response).encode())
            return
        elif self.path == '/api/v1/session' or self.path == '/api/v1/sessions':  # For Argo CD login
            self._set_headers()
            response = {
                "token": "mock-argocd-token-for-development",
                "refreshToken": "mock-refresh-token"
            }
            self.wfile.write(json.dumps(response).encode())
            return
            
        # Default response for other POST requests
        self._set_headers()
        self.wfile.write(json.dumps({
            "kind": "Status",
            "apiVersion": "v1",
            "metadata": {},
            "status": "Success",
            "message": f"Resource created at: {self.path}"
        }).encode())

def run(server_class=HTTPServer, handler_class=MockKubernetesHandler, port=8001):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting mock Kubernetes API server on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
