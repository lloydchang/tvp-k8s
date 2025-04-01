"""
README.md Generator Script

This script generates the project README.md file by combining:
1. The TVP header documentation from tvp_header.md
2. A table of contents for easy navigation
3. System architecture diagrams rendered from Mermaid syntax files
4. The TVP footer documentation from tvp_footer.md

The script reads Mermaid diagram files from the mermaid/ directory
and inserts them into the README.md with appropriate section headers.
"""

import os
import re

# List of Mermaid diagram files and their corresponding section titles
mermaid_files = [
    "mermaid/tvp-architecture-diagram.mermaid",
    "mermaid/tvp-reconciliation-sequence.mermaid",
    "mermaid/component-diagram.mermaid",
    "mermaid/data-flow-diagram.mermaid",
    "mermaid/api-structure-diagram.mermaid",
    "mermaid/health-check-sequence.mermaid",
    "mermaid/kubernetes-proxy-sequence.mermaid",
    "mermaid/argo-cd-authentication-sequence.mermaid",
    "mermaid/app-deployment-workflow.mermaid",
]

titles = [
    "TVP GitOps Architecture",
    "TVP GitOps Reconciliation Sequence",
    "Component Interaction Diagram",
    "Data Flow Diagram",
    "API Structure Diagram",
    "Health Check Sequence",
    "Kubernetes Proxy Sequence",
    "Argo CD Authentication Sequence",
    "Application Deployment Workflow",
]

def create_toc_link(title, index):
    """
    Convert a title to a GitHub-compatible markdown anchor link.
    
    Args:
        title: The section title
        index: The section number
        
    Returns:
        A string containing the markdown link to the section
    """
    # Convert the title to lowercase and replace spaces with hyphens for the anchor
    anchor = f"{index+1}-{re.sub(r'[^\w\s-]', '', title).lower().replace(' ', '-')}"
    return f"- [{index+1}. {title}](#{anchor})"

def main():
    """
    Main function that generates the README.md file.
    
    Reads the TVP header content and Mermaid diagram files,
    creates a table of contents, writes them to the README.md file,
    and finally appends the TVP footer content if available.
    
    If a file is missing, it will include a placeholder message.
    """
    readme_path = os.path.join(os.path.dirname(__file__), "../README.md")
    with open(readme_path, "w") as readme:
        # Read and write the TVP header from the separate file
        try:
            with open("tvp_header.md", "r") as header_file:
                tvp_header = header_file.read()
                readme.write(tvp_header + "\n\n")
        except FileNotFoundError:
            readme.write("# System Architecture Documentation:\n\n")
            readme.write("This [README.md](https://github.com/lloydchang/tvp/blob/main/README.md) provides a visual overview of the system architecture using various diagrams.\n\n")
        
        # Create and write the table of contents
        readme.write("## Table of Contents\n\n")
        for i, title in enumerate(titles):
            toc_link = create_toc_link(title, i)
            readme.write(f"{toc_link}\n")
        readme.write("\n")
        
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
            
        # Finally, append the TVP footer if it exists
        try:
            with open("tvp_footer.md", "r") as footer_file:
                tvp_footer = footer_file.read()
                readme.write(tvp_footer + "\n")
        except FileNotFoundError:
            # If footer file is not found, just continue without it
            pass

if __name__ == "__main__":
    main()
