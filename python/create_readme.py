import os

mermaid_files = [
    "mermaid/component-diagram.mermaid",
    "mermaid/api-structure-diagram.mermaid",
    "mermaid/argocd-authentication-sequence.mermaid",
    "mermaid/kubernetes-proxy-sequence.mermaid",
    "mermaid/tvp-reconciliation-sequence.mermaid",
    "mermaid/health-check-sequence.mermaid",
    "mermaid/tvp-architecture-diagram.mermaid",
    "mermaid/app-deployment-workflow.mermaid",
    "mermaid/data-flow-diagram.mermaid"
]

titles = [
    "Component Interaction Diagram",
    "API Structure Diagram",
    "ArgoCD Authentication Sequence",
    "Kubernetes Proxy Sequence",
    "TVP GitOps Reconciliation Sequence",
    "Health Check Sequence",
    "TVP GitOps Architecture",
    "Application Deployment Workflow",
    "Data Flow Diagram"
]

with open("../README.md", "w") as readme:
    # Read and write the TVP header from the separate file
    try:
        with open("tvp_header.md", "r") as header_file:
            tvp_header = header_file.read()
            readme.write(tvp_header + "\n\n")
    except FileNotFoundError:
        readme.write("# System Architecture Documentation\n\n")
        readme.write("This [README.md](https://github.com/lloydchang/tvp/blob/main/README.md) provides a visual overview of the system architecture using various diagrams.\n\n")
    
    # Then write the diagrams
    for i, (filename, title) in enumerate(zip(mermaid_files, titles)):
        readme.write(f"## {i+1}. {title}\n\n")
        readme.write("```mermaid\n")
        
        try:
            with open(filename, "r") as mermaid_file:
                mermaid_content = mermaid_file.read()
                readme.write(mermaid_content)
        except FileNotFoundError:
            readme.write(f"# File {filename} not found\n")
        
        readme.write("\n```\n\n")
