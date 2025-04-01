"""
README.md Generator Script

This script generates the project README.md file by combining:
1. The TVP header documentation from tvp_header.md
2. A table of contents for easy navigation
3. Narrative introduction and section transitions
4. System architecture diagrams with explanatory text
5. The TVP footer documentation from tvp_footer.md

The script creates a coherent narrative while preserving quotations and diagrams.
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
    "mermaid/argo-cd-proxy-sequence.mermaid",
    "mermaid/app-deployment-workflow.mermaid"
]

# Titles organized in a logical flow for the narrative
titles = [
    "TVP GitOps Architecture",
    "TVP GitOps Reconciliation Sequence",
    "Component Interaction Diagram",
    "Data Flow Diagram", 
    "API Structure Diagram",
    "Health Check Sequence",
    "Kubernetes Proxy Sequence",
    "Argo CD Proxy Sequence",
    "Application Deployment Workflow"
]

# Introductions for each section to create narrative flow
section_intros = [
    "Let's start by understanding the overall architecture of our Thinnest Viable Platform and how it implements GitOps principles. This diagram provides a high-level view of the system components and their interactions:",
    
    "Now that we've seen the architecture, let's examine how the GitOps reconciliation process works in practice. This sequence diagram shows the steps involved when synchronizing the platform with the Git repository:",
    
    "To better understand the internal structure of the TVP, the following component interaction diagram breaks down the FastAPI application into its functional parts and shows how they communicate:",
    
    "The data flows through the system in a specific pattern. This diagram illustrates how information moves between different components of the platform:",
    
    "Our API is structured to provide clear separation of concerns while maintaining simplicity. The following class diagram shows the architecture of our API endpoints and their supporting classes:",
    
    "Reliability is essential for any platform. The health check mechanism ensures that all services are operating correctly. Here's how the health check sequence works:",
    
    "The Kubernetes Proxy allows users to interact with the Kubernetes API through our platform. This sequence diagram shows how requests are securely proxied:",
    
    "Similar to the Kubernetes proxy, the Argo CD proxy enables interaction with Argo CD through our platform. The sequence diagram below shows the authentication flow:",
    
    "Finally, let's look at the application deployment workflow. This state diagram shows the complete lifecycle of an application deployment through our platform:"
]

# Transitions between sections to improve narrative flow
section_transitions = [
    "With the architecture overview in mind, we can now explore how the platform handles GitOps reconciliation.",
    
    "Understanding the reconciliation process helps us see how changes propagate through the system. Let's now look at the component structure in more detail.",
    
    "These components work together to facilitate various data flows within the platform.",
    
    "Now that we understand the data flow, let's examine the API structure that enables these interactions.",
    
    "One of the key aspects of our API is the ability to monitor system health.",
    
    "In addition to health monitoring, our platform provides secure access to the underlying Kubernetes API.",
    
    "Similarly, our platform facilitates interaction with Argo CD for GitOps operations.",
    
    "All these components and interactions come together in the application deployment workflow.",
    
    "This workflow represents the culmination of all the previously described processes working in harmony to deliver a streamlined developer experience."
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

def contains_architecture_section(content):
    """
    Check if content already contains a system architecture section heading.
    
    Args:
        content: The content to check
        
    Returns:
        True if it contains architecture heading, False otherwise
    """
    return re.search(r'#+ +System +Architecture', content, re.IGNORECASE) is not None

def main():
    """
    Main function that generates the README.md file.
    
    Reads the TVP header content, creates a table of contents,
    and then writes diagrams with narrative text to create a
    coherent document flow. Finally adds the footer.
    
    If a file is missing, it will include a placeholder message.
    """
    readme_path = os.path.join(os.path.dirname(__file__), "../README.md")
    header_content = ""
    
    # Read the TVP header content
    try:
        with open("tvp_header.md", "r") as header_file:
            header_content = header_file.read()
    except FileNotFoundError:
        header_content = "# Thinnest Viable Platform (TVP) about Leverage\n\n"
        header_content += "This [README.md](https://github.com/lloydchang/tvp/blob/main/README.md) provides a visual overview of the system architecture using various diagrams.\n\n"
    
    with open(readme_path, "w") as readme:
        # Write the header content
        readme.write(header_content + "\n")
        
        # Add a smooth transition from conceptual content to technical diagrams
        if not contains_architecture_section(header_content):
            readme.write("## System Architecture Documentation\n\n")
        else:
            # Add a bridging paragraph if architecture section already exists
            readme.write("\n# Implementation of TVP Principles\n\n")
            readme.write("Now that we've explored the conceptual foundations of Thinnest Viable Platform, ")
            readme.write("let's examine how these principles are implemented in our architecture. ")
            readme.write("The following sections illustrate the practical application of TVP concepts ")
            readme.write("through various architectural and interaction diagrams.\n\n")
        
        # Add the general introduction about the diagrams
        readme.write("The following diagrams provide a comprehensive overview of the TVP architecture. ")
        readme.write("Each diagram highlights a different aspect of the system, from high-level architecture ")
        readme.write("to specific interaction sequences, demonstrating how our implementation delivers ")
        readme.write("leverage through self-service APIs.\n\n")
        
        # Create and write the table of contents
        readme.write("## Table of Contents\n\n")
        for i, title in enumerate(titles):
            toc_link = create_toc_link(title, i)
            readme.write(f"{toc_link}\n")
        readme.write("\n")
        
        # Then write the diagrams with narrative text
        for i, (filename, title, intro, transition) in enumerate(zip(mermaid_files, titles, section_intros, section_transitions)):
            # Write section header and introduction
            readme.write(f"## {i+1}. {title}\n\n")
            readme.write(f"{intro}\n\n")
            
            # Write the diagram
            readme.write("```mermaid\n")
            try:
                with open(filename, "r") as mermaid_file:
                    mermaid_content = mermaid_file.read()
                    readme.write(mermaid_content)
            except FileNotFoundError:
                readme.write(f"# File {filename} not found\n")
            readme.write("\n```\n\n")
            
            # Add transition to next section (except for the last one)
            if i < len(mermaid_files) - 1:
                readme.write(f"{transition}\n\n")
        
        # Add a conclusion to tie everything together
        readme.write("## Conclusion\n\n")
        readme.write("The diagrams presented above provide a comprehensive view of our Thinnest Viable Platform architecture. ")
        readme.write("By implementing a GitOps approach with careful attention to component interaction and data flow, ")
        readme.write("we've created a platform that provides leverage through self-service APIs while maintaining simplicity and ease of use. ")
        readme.write("This platform embodies the TVP concept by offering just enough functionality to accelerate application teams ")
        readme.write("without the burden of unnecessary complexity.\n\n")
            
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
