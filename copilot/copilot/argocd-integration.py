import yaml
from fastapi import FastAPI, HTTPException
from kubernetes import client, config
from git import Repo
import os

class ArgoCDIntegrator:
    def __init__(self, 
                 git_repo_path='/tmp/app-manifests',
                 argocd_repo_url='https://github.com/your-org/kubernetes-manifests'):
        """
                 Initialize the ArgoCDIntegrator instance.
                 
                 Sets up the local Git repository for storing ArgoCD manifests. If the repository
                 is not found at the specified path, it is cloned from the given remote URL; otherwise,
                 the existing repository is loaded.
                 
                 Args:
                     git_repo_path: Local directory path for the repository. Defaults to '/tmp/app-manifests'.
                     argocd_repo_url: Remote Git URL to clone the repository from if not present.
                         Defaults to 'https://github.com/your-org/kubernetes-manifests'.
                 """
                 self.git_repo_path = git_repo_path
        self.argocd_repo_url = argocd_repo_url
        
        # Ensure repo exists or clone
        if not os.path.exists(git_repo_path):
            self.repo = Repo.clone_from(argocd_repo_url, git_repo_path)
        else:
            self.repo = Repo(git_repo_path)

    def generate_application_manifest(self, 
                                      app_name: str, 
                                      git_source: str, 
                                      k8s_target_namespace: str):
        """
                                      Generate an ArgoCD Application manifest.
                                      
                                      Constructs an ArgoCD Application Custom Resource manifest as a dictionary. The manifest
                                      includes metadata with the application name (appending "-application"), source settings
                                      with the Git repository URL and a fixed target revision and path, and a destination
                                      configured to deploy to the specified Kubernetes namespace. It also sets up a sync
                                      policy for automated pruning and self-healing.
                                      
                                      Args:
                                          app_name: The base name for the application.
                                          git_source: URL of the Git repository containing the application.
                                          k8s_target_namespace: Kubernetes namespace where the application will be deployed.
                                      
                                      Returns:
                                          A dictionary representing the ArgoCD Application manifest.
                                      """
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
        """
        Commit and push the ArgoCD application manifest to the Git repository.
        
        This method creates or updates a directory for the specified application under the
        configured Git repository path, writes the provided manifest as a YAML file, and then
        stages, commits, and pushes the changes to the remote repository.
        
        Args:
            app_name (str): The name of the application, used for directory creation and commit message.
            manifest: A dictionary representing the ArgoCD application manifest.
        """
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
    Creates an ArgoCD application for deployment.
    
    Generates an ArgoCD manifest with the provided application name, Git source, and 
    target Kubernetes namespace, then commits the manifest to a Git repository. Returns 
    a dictionary indicating the deployment initiation status and details. Raises an 
    HTTPException with a 500 status code if an error occurs.
      
    Args:
        app_name: The name of the application to be deployed.
        git_source: The Git source reference for the application manifest.
        namespace: The Kubernetes namespace for the application (default is "default").
      
    Returns:
        A dictionary containing the deployment status and details including app_name, 
        git_source, and namespace.
      
    Raises:
        HTTPException: If an error occurs during manifest generation or Git operations.
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
