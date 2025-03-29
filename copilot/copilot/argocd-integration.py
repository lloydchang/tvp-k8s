import yaml
from fastapi import FastAPI, HTTPException
from kubernetes import client, config
from git import Repo
import os

class ArgoCDIntegrator:
    def __init__(self, 
                 git_repo_path='/tmp/app-manifests',
                 argocd_repo_url='https://github.com/your-org/kubernetes-manifests'):
        self.git_repo_path = git_repo_path
        self.argocd_repo_url = argocd_repo_url
        
        # Ensure repo exists or clone
        if not os.path.exists(git_repo_path):
            Repo.clone_from(argocd_repo_url, git_repo_path)
        else:
            self.repo = Repo(git_repo_path)

    def generate_application_manifest(self, 
                                      app_name: str, 
                                      git_source: str, 
                                      k8s_target_namespace: str):
        """Generate ArgoCD Application Custom Resource"""
        argocd_app = {
            'apiVersion': 'argoproj.io/v1alpha1',
            'kind': 'Application',
            'metadata': {
                'name': f'{app_name}-application',
                'namespace': 'argocd'
            },
            'spec': {
                'project': 'default',
                'source': {
                    'repoURL': git_source,
                    'targetRevision': 'HEAD',
                    'path': f'apps/{app_name}'
                },
                'destination': {
                    'server': 'https://kubernetes.default.svc',
                    'namespace': k8s_target_namespace
                },
                'syncPolicy': {
                    'automated': {
                        'prune': True,
                        'selfHeal': True
                    }
                }
            }
        }
        return argocd_app

    def commit_and_push_manifest(self, app_name: str, manifest):
        """Commit and push ArgoCD application manifest to Git"""
        app_dir = os.path.join(self.git_repo_path, f'apps/{app_name}')
        os.makedirs(app_dir, exist_ok=True)
        
        manifest_path = os.path.join(app_dir, 'application.yaml')
        
        with open(manifest_path, 'w') as f:
            yaml.dump(manifest, f)
        
        self.repo.git.add(manifest_path)
        self.repo.git.commit('-m', f'Add ArgoCD manifest for {app_name}')
        self.repo.git.push()

app = FastAPI(title="ArgoCD Integration Platform")

@app.post("/deploy")
async def create_argocd_application(
    app_name: str, 
    git_source: str, 
    namespace: str = 'default'
):
    """
    Create an ArgoCD application by generating a manifest 
    and committing it to a Git repository
    """
    try:
        integrator = ArgoCDIntegrator()
        
        # Generate ArgoCD application manifest
        argocd_manifest = integrator.generate_application_manifest(
            app_name, 
            git_source, 
            namespace
        )
        
        # Commit manifest to Git
        integrator.commit_and_push_manifest(app_name, argocd_manifest)
        
        return {
            "status": "Application deployment initiated",
            "details": {
                "app_name": app_name,
                "git_source": git_source,
                "namespace": namespace
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
