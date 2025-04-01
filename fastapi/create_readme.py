"""
README.md Generator Script

This script generates the project README.md file by combining:
1. The TVP header documentation from tvp_header.md
2. System architecture diagrams rendered from Mermaid syntax files

The script reads Mermaid diagram files from the mermaid/ directory
and inserts them into the README.md with appropriate section headers.
"""

import os

# List of Mermaid diagram files and their corresponding section titles
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

def main():
    """
    Main function that generates the README.md file.
    
    Reads the TVP header content and Mermaid diagram files,
    then writes them to the README.md file in the correct order.
    
    If a file is missing, it will include a placeholder message.
    """
    with open("../README.md", "w") as readme:
        # Read and write the TVP header from the separate file
        try:
            with open("tvp_header.md", "r") as header_file:
                tvp_header = header_file.read()
                readme.write(tvp_header + "\n\n")
        except FileNotFoundError:
            readme.write("# System Architecture Documentation:\n\n")
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

if __name__ == "__main__":
    main()
