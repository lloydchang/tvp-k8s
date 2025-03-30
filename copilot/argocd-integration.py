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
                 Initializes the ArgoCDIntegrator instance.
                 
                 Sets the local Git repository path and ArgoCD repository URL. If the local repository
                 does not exist at the specified path, the repository is cloned from the remote URL;
                 otherwise, the existing repository is initialized.
                 
                 Args:
                     git_repo_path: Local filesystem path for the Git repository containing application manifests.
                     argocd_repo_url: URL of the remote Git repository to clone if the local repository is absent.
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
                                      
                                      Builds and returns a dictionary representing an ArgoCD Application Custom
                                      Resource with preset metadata, source details, destination, and automated
                                      sync policies.
                                      
                                      Args:
                                          app_name (str): The base name for the application, used to construct the resource name.
                                          git_source (str): The Git repository URL for the application source.
                                          k8s_target_namespace (str): The Kubernetes namespace where the application is deployed.
                                      
                                      Returns:
                                          dict: A dictionary describing the ArgoCD Application manifest.
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
        Commits and pushes the ArgoCD application manifest to the Git repository.
        
        This method creates the target application directory if it does not exist,
        writes the provided manifest to an 'application.yaml' file, stages the file,
        commits the change with a message that includes the application name, and
        pushes the commit to the remote repository.
        
        Args:
            app_name: The name of the application, used to determine the directory path and commit message.
            manifest: A dictionary representing the ArgoCD manifest to be written and committed.
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
    Initiate an ArgoCD application deployment.
    
    This asynchronous function constructs an ArgoCD application manifest using the
    specified application name, Git source, and Kubernetes namespace. It then commits
    the manifest to a Git repository and returns a response indicating that the deployment
    has been initiated. An HTTPException is raised if any error occurs during the process.
    
    Args:
        app_name (str): The name of the application to deploy.
        git_source (str): The Git repository source for the application.
        namespace (str, optional): The Kubernetes namespace for the deployment.
                                   Defaults to 'default'.
    
    Returns:
        dict: A dictionary containing the deployment status and details including the
              application name, git source, and namespace.
    
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
