"""
README.md Generator Script

This script generates the project README.md file by combining:
1. The TVP header documentation from tvp_header.md
2. A table of contents for easy navigation
3. Narrative introduction and section transitions
4. System architecture diagrams with explanatory text and leverage points
5. Metrics for measuring platform leverage
6. The TVP footer documentation from tvp_footer.md

The script creates a coherent narrative that consistently emphasizes the concept of leverage.
"""

import os
import re
from datetime import datetime

# List of Mermaid diagram files in a logical narrative sequence
mermaid_files = [
    "mermaid/gitops-architecture-diagram.mermaid",
    "mermaid/gitops-workflow-diagram.mermaid",
    "mermaid/gitops-reconciliation-sequence.mermaid",
    "mermaid/component-diagram.mermaid",
    "mermaid/data-flow-diagram.mermaid",
    "mermaid/api-structure-diagram.mermaid",
    "mermaid/health-check-sequence.mermaid",
    "mermaid/kubernetes-proxy-sequence.mermaid",
    "mermaid/argo-cd-proxy-sequence.mermaid",
    "mermaid/app-deployment-workflow.mermaid",
    "mermaid/test-coverage-diagram.mermaid",
]

# Titles precisely matching the content of each diagram
titles = [
    "GitOps Architecture Overview",
    "GitOps Workflow Sequence",
    "GitOps Reconciliation Process",
    "Component Interaction Diagram",
    "Data Flow Diagram", 
    "API Structure Diagram",
    "Health Check Sequence",
    "Kubernetes Proxy Sequence",
    "Argo CD Proxy Sequence",
    "Application Deployment Workflow",
    "Test Coverage Structure",
]

# Introductions for each section to create narrative flow - revised for stronger narrative arc
section_intros = [
    # Exposition - Setting the stage and introducing the problem
    "Let's start by understanding the challenge: how can a lean platform team support hundreds of engineers efficiently? Our Thinnest Viable Platform architecture provides the answer. This diagram shows the high-level view of the system components and their interactions, revealing how the platform creates leverage through carefully designed abstractions:",
    
    # Rising action - Building complexity and engagement
    "With our architectural foundation established, let's see how engineers actually interact with this system. The GitOps workflow represents the primary interface between engineers and infrastructure, making complex operations remarkably simple. This sequence diagram illustrates the streamlined experience when an engineer pushes a change:",
    
    "Behind this simplified developer experience lies a sophisticated reconciliation process. As complexity builds, we see how the platform automatically keeps environments synchronized with the desired state in Git, eliminating manual toil:",
    
    "Diving deeper into the system's inner workings, we can examine the components that power our platform. This interaction diagram reveals how the FastAPI application is structured to maximize maintainability and separation of concerns:",
    
    "These components don't exist in isolation - they communicate through carefully designed data flows that minimize redundancy and create consistency. As our story progresses, this diagram shows how information moves between components, creating standardized patterns:",
    
    # Approaching climax - Reaching peak complexity
    "At the heart of our platform lies the API structure - the central interface that ties everything together. This diagram reveals the elegant organization of endpoints in api/index.py, showing how complexity is contained and exposed through simple interfaces:",
    
    "With increased complexity comes the need for reliability. The health check mechanism acts as the platform's nervous system, constantly monitoring component states to ensure operational integrity. This sequence shows how health checks verify system readiness:",
    
    # Climax - The most critical interactions
    "We've now reached the core capability of our platform: secure access to underlying infrastructure. The Kubernetes Proxy represents the primary leverage point, where platform engineering effort creates enormous value. This diagram shows how the proxy securely connects engineers to Kubernetes without requiring specialized expertise:",
    
    "Similarly critical is our Argo CD integration, which extends the platform's reach to GitOps deployment workflows. The proxy flow shown here creates a seamless experience for engineers while maintaining security boundaries:",
    
    # Falling action - Showing resolution of complexity
    "All these components and interactions culminate in the application deployment workflow. This state diagram shows how the various parts work in harmony to deliver applications from code to production, resolving the complexity we've built up throughout our journey:",
    
    # Resolution - Demonstrating stability and sustainability
    "To ensure this system remains stable and can evolve over time, comprehensive testing underpins everything. This final diagram shows how test coverage validates each component, creating confidence that the platform will continue to deliver leverage:"
]

# Transitions between sections to improve narrative flow - enhanced for dramatic tension
section_transitions = [
    "Now that we've established the architectural foundation, let's see how engineers actually interact with this powerful system.",
    
    "While this workflow appears simple from the engineer's perspective, there's sophisticated automation working behind the scenes. Let's examine the reconciliation process that makes this seamless experience possible.",
    
    "To understand how reconciliation works at a deeper level, we need to look at the individual components that make up our platform.",
    
    "With these components identified, we can follow how data flows through the system, creating patterns that engineers can rely on.",
    
    "As our exploration deepens, we arrive at the crucial API structure that serves as the interface between users and platform functionality.",
    
    "A sophisticated platform needs to be reliable. Let's see how health monitoring ensures the system remains operational even as complexity increases.",
    
    "Now we reach the crucial capability that delivers immense leverage: abstracting away Kubernetes complexity through our proxy system.",
    
    "With Kubernetes access solved, we complete our core capabilities by providing similar abstraction for GitOps workflows through the Argo CD proxy.",
    
    "With all these elements in place, we can now see how they combine to create a complete application deployment workflow - the ultimate value proposition of our platform.",
    
    "Underpinning this entire system is a comprehensive testing strategy that ensures reliability and sustainability.",
    
    "With all these pieces functioning together, our platform delivers the force multiplication effect that is the essence of leverage."
]

# Leverage points that highlight how each component provides leverage
leverage_points = [
    "**Leverage Point:** The GitOps architecture — [**_Declarative_**, versioned, immutable, **_Pulled automatically_** and **_continuously Reconciled_**](https://opengitops.dev/) — creates leverage by allowing a lean platform team to support hundreds of engineers. By centralizing the infrastructure interaction through a single API layer, the organization gains a force multiplier where each platform engineer's work impacts hundreds of engineers.",
    
    "**Leverage Point:** The GitOps workflow provides leverage by enabling a declarative approach to infrastructure. This means that one engineer's work can affect multiple environments consistently, and the source of truth remains in version control rather than in manual configurations.",

    "**Leverage Point:** The reconciliation process provides leverage by automating what would otherwise be manual, error-prone operations. One engineer committing a change to Git can trigger consistent updates across multiple environments and services - a significant force multiplier.",
    
    "**Leverage Point:** This component structure demonstrates the leverage principle of TVP by separating concerns and enabling multiple teams to work independently. Each component acts as a force multiplier by providing standardized functionality that would otherwise be duplicated across teams.",
    
    "**Leverage Point:** The data flow design creates leverage by standardizing how information moves through the system. This eliminates redundant data handling code across applications and ensures consistent security practices without requiring each team to become security experts.",
    
    "**Leverage Point:** The API structure provides leverage by offering clear, consistent interfaces that hide implementation complexity. Engineering teams can focus on their business logic while the platform handles infrastructure concerns - a classic example of how abstraction creates leverage.",
    
    "**Leverage Point:** The health check system creates leverage by centralizing monitoring. Rather than each team building their own health monitoring, the platform provides this as a service, multiplying the effectiveness of operational efforts.",
    
    "**Leverage Point:** The Kubernetes proxy demonstrates leverage by providing secure, consistent access to Kubernetes resources without requiring each engineer to understand Kubernetes authentication and API complexities. One implementation serves many consumers.",
    
    "**Leverage Point:** The Argo CD proxy creates leverage by abstracting away the complexities of GitOps tooling. This allows engineering teams to benefit from GitOps workflows without needing to become Argo CD experts, multiplying the impact of the platform team's expertise.",
    
    "**Leverage Point:** This Application Deployment Workflow demonstrates how TVP creates leverage through standardization and automation. Engineering teams follow a consistent path to production, benefiting from platform capabilities that would be prohibitively expensive for each team to build independently.",
    
    "**Leverage Point:** Comprehensive test coverage creates leverage by ensuring that platform updates don't introduce regressions. This provides confidence to both the platform team and application engineers, enabling faster iteration and more frequent releases.",
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

def read_markdown_file(filename, default_content=""):
    """
    Read content from a markdown file.
    
    Args:
        filename: Path to the markdown file
        default_content: Content to return if the file is not found
        
    Returns:
        The content of the file or the default content if the file is not found
    """
    try:
        with open(filename, "r") as file:
            content = file.read()
            # Remove the filepath comment if present
            content = re.sub(r'^<!-- filepath:.*? -->', '', content, flags=re.MULTILINE).strip()
            return content
    except FileNotFoundError:
        print(f"Warning: {filename} not found, using default content.")
        return default_content

def main():
    """
    Main function that generates the README.md file.
    
    Reads the TVP header content, creates a table of contents,
    adds diagrams with narrative text and leverage points,
    includes metrics for measuring leverage, and finally adds the footer.
    
    If a file is missing, it will include a placeholder message.
    """
    readme_path = os.path.join(os.path.dirname(__file__), "../README.md")
    header_content = ""
    
    # Read the TVP header content
    try:
        with open("markdown/tvp_header.md", "r") as header_file:
            header_content = header_file.read()
    except FileNotFoundError:
        header_content = "# Thinnest Viable Platform (TVP) about Leverage\n\n"
        header_content += "This README.md provides a visual overview of the system architecture using various diagrams.\n\n"
    
    # Read the measuring leverage and conclusion content
    measuring_leverage_content = read_markdown_file(
        "markdown/measuring_platform_leverage.md",
        "**The proof is in the numbers.** When leverage is properly applied, the results are dramatic and measurable. Here are sample metrics that our TVP approach may deliver..."
    )
    
    conclusion_content = read_markdown_file(
        "markdown/conclusion_the_multiplication_of_force.md",
        "Throughout this architectural journey, we've seen how the Thinnest Viable Platform embodies Archimedes' famous principle: \"Give me a lever long enough and a fulcrum on which to place it, and I shall move the world.\"..."
    )
    
    with open(readme_path, "w") as readme:
        # Write the header content
        readme.write(header_content + "\n")
        
        # Add a dramatic hook at the beginning to engage readers immediately
        if not contains_architecture_section(header_content):
            readme.write("## System Architecture Documentation\n\n")
        else:
            # Enhanced bridging paragraph with stronger hook and tension
            readme.write("\n# Implementation of TVP Principles for Maximum Leverage\n\n")
            readme.write("**The challenge:** How can organizations scale their development capabilities without proportionally scaling their operational overhead? ")
            readme.write("The answer lies in leverage - the ability for small teams to enable disproportionately large outcomes. ")
            readme.write("In the following sections, we'll journey through the architecture of a Thinnest Viable Platform ")
            readme.write("that embodies this principle, showing how carefully designed abstractions create ")
            readme.write("extraordinary force multiplication across an engineering organization.\n\n")
        
        # Enhanced general introduction with more narrative tension
        readme.write("The diagrams below tell a story - one of complexity tamed through deliberate design choices. ")
        readme.write("We'll start with the big picture and progressively dive deeper, revealing how ")
        readme.write("each component contributes to the platform's leverage. Pay attention to how a few ")
        readme.write("well-designed interfaces and automation points eliminate entire categories of toil ")
        readme.write("across the organization, allowing engineering teams to focus on business value rather than infrastructure complexities.\n\n")
        
        # Create and write the table of contents
        readme.write("## Table of Contents\n\n")
        for i, title in enumerate(titles):
            toc_link = create_toc_link(title, i)
            readme.write(f"{toc_link}\n")
        readme.write(f"- [{len(titles)+1}. Measuring Platform Leverage](#{len(titles)+1}-measuring-platform-leverage)\n")
        readme.write(f"- [{len(titles)+2}. Conclusion: The Multiplication of Force](#{len(titles)+2}-conclusion-the-multiplication-of-force)\n\n")
        
        # Then write the diagrams with narrative text and leverage points
        for i, (filename, title, intro, transition, leverage) in enumerate(zip(mermaid_files, titles, section_intros, section_transitions, leverage_points)):
            # Write section header and introduction
            readme.write(f"## {i+1}. {title}\n\n")
            readme.write(f"{intro}\n\n")
            
            # Write the diagram
            readme.write("```mermaid\n")
            try:
                with open(filename, "r") as mermaid_file:
                    mermaid_content = mermaid_file.read()
                    # Remove the filepath comment to avoid showing it in the README
                    mermaid_content = re.sub(r'^// filepath:.*$', '', mermaid_content, flags=re.MULTILINE).strip()
                    readme.write(mermaid_content)
            except FileNotFoundError:
                readme.write(f"# File {filename} not found\n")
            readme.write("\n```\n\n")
            
            # Add the leverage point
            readme.write(f"{leverage}\n\n")
            
            # Add transition to next section (except for the last one)
            if i < len(mermaid_files) - 1:
                readme.write(f"{transition}\n\n")
        
        # Metrics section from markdown file
        readme.write(f"## {len(titles)+1}. Measuring Platform Leverage\n\n")
        readme.write(measuring_leverage_content + "\n\n")

        # Conclusion section from markdown file
        readme.write(f"## {len(titles)+2}. Conclusion: The Multiplication of Force\n\n")
        readme.write(conclusion_content + "\n\n")
        
        # Finally, append the TVP footer if it exists
        try:
            with open("markdown/tvp_footer.md", "r") as footer_file:
                tvp_footer = footer_file.read()
                readme.write(tvp_footer + "\n")
        except FileNotFoundError:
            # If footer file is not found, just continue without it
            pass

if __name__ == "__main__":
    main()
