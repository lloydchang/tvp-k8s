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

# Introductions for each section to create narrative flow - now with more emphasis on leverage
section_intros = [
    "Let's start by understanding the overall architecture of our Thinnest Viable Platform and how it implements GitOps principles to provide leverage. This diagram provides a high-level view of the system components and their interactions:",
    
    "Now that we've seen the architecture, let's examine how the GitOps reconciliation process works in practice. This sequence diagram shows the steps involved when synchronizing the platform with the Git repository - a key automation that creates leverage:",
    
    "To better understand how the TVP creates leverage, the following component interaction diagram breaks down the FastAPI application into its functional parts and shows how they communicate to reduce duplicated work across teams:",
    
    "The data flows through the system in a specific pattern, creating efficiency through standardization. This diagram illustrates how information moves between different components of the platform:",
    
    "Our API is structured to provide clear separation of concerns while maintaining simplicity - a core TVP principle. The following class diagram shows the architecture of our API endpoints and their supporting classes:",
    
    "Reliability is essential for any platform that aims to provide leverage. The health check mechanism ensures that all services are operating correctly, reducing the monitoring burden on application teams:",
    
    "The Kubernetes Proxy allows application developers to interact with the Kubernetes API through our platform, providing leverage by abstracting away complexity. This sequence diagram shows how requests are securely proxied:",
    
    "Similar to the Kubernetes proxy, the Argo CD proxy enables interaction with Argo CD through our platform, reducing the cognitive load for developers. The sequence diagram below shows the authentication flow:",
    
    "Finally, let's look at the application deployment workflow. This state diagram shows the complete lifecycle of an application deployment through our platform, demonstrating how the TVP provides leverage throughout the deployment process:"
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

# New: Leverage points that highlight how each component provides leverage to the organization
leverage_points = [
    "**Leverage Point:** The GitOps architecture creates leverage by allowing a small platform team to support many development teams. By centralizing the infrastructure interaction through a single API layer, the organization gains a force multiplier where each platform engineer's work impacts dozens of application developers.",
    
    "**Leverage Point:** The reconciliation process provides leverage by automating what would otherwise be manual, error-prone operations. One developer committing a change to Git can trigger consistent updates across multiple environments and services - a significant force multiplier.",
    
    "**Leverage Point:** This component structure demonstrates the leverage principle of TVP by separating concerns and enabling multiple teams to work independently. Each component acts as a force multiplier by providing standardized functionality that would otherwise be duplicated across teams.",
    
    "**Leverage Point:** The data flow design creates leverage by standardizing how information moves through the system. This eliminates redundant data handling code across applications and ensures consistent security practices without requiring each team to become security experts.",
    
    "**Leverage Point:** The API structure provides leverage by offering clear, consistent interfaces that hide implementation complexity. Development teams can focus on their business logic while the platform handles infrastructure concerns - a classic example of how abstraction creates leverage.",
    
    "**Leverage Point:** The health check system creates leverage by centralizing monitoring. Rather than each team building their own health monitoring, the platform provides this as a service, multiplying the effectiveness of operational efforts.",
    
    "**Leverage Point:** The Kubernetes proxy demonstrates leverage by providing secure, consistent access to Kubernetes resources without requiring each developer to understand Kubernetes authentication and API complexities. One implementation serves many consumers.",
    
    "**Leverage Point:** The Argo CD proxy creates leverage by abstracting away the complexities of GitOps tooling. This allows development teams to benefit from GitOps workflows without needing to become Argo CD experts, multiplying the impact of the platform team's expertise.",
    
    "**Leverage Point:** This workflow demonstrates how TVP creates leverage through standardization and automation. Development teams follow a consistent path to production, benefiting from platform capabilities that would be prohibitively expensive for each team to build independently."
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
    adds diagrams with narrative text and leverage points,
    includes metrics for measuring leverage, and finally adds the footer.
    
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
            readme.write("\n# Implementation of TVP Principles for Maximum Leverage\n\n")
            readme.write("Now that we've explored the conceptual foundations of Thinnest Viable Platform, ")
            readme.write("let's examine how these principles are implemented in our architecture to create leverage. ")
            readme.write("The following sections illustrate the practical application of TVP concepts ")
            readme.write("through various architectural and interaction diagrams, highlighting ")
            readme.write("how each component contributes to the overall force multiplication effect.\n\n")
        
        # Add the general introduction about the diagrams
        readme.write("The following diagrams provide a comprehensive overview of the TVP architecture. ")
        readme.write("Each diagram highlights a different aspect of the system, from high-level architecture ")
        readme.write("to specific interaction sequences, demonstrating how our implementation delivers ")
        readme.write("leverage through self-service APIs and automation. Consider how each component ")
        readme.write("multiplies the effectiveness of both the platform team and development teams.\n\n")
        
        # Create and write the table of contents
        readme.write("## Table of Contents\n\n")
        for i, title in enumerate(titles):
            toc_link = create_toc_link(title, i)
            readme.write(f"{toc_link}\n")
        readme.write("- [10. Measuring Platform Leverage](#10-measuring-platform-leverage)\n")
        readme.write("- [11. Conclusion](#11-conclusion)\n\n")
        
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
                    readme.write(mermaid_content)
            except FileNotFoundError:
                readme.write(f"# File {filename} not found\n")
            readme.write("\n```\n\n")
            
            # Add the leverage point
            readme.write(f"{leverage}\n\n")
            
            # Add transition to next section (except for the last one)
            if i < len(mermaid_files) - 1:
                readme.write(f"{transition}\n\n")
        
        # Add a section on measuring platform leverage
        readme.write("## 10. Measuring Platform Leverage (in a hypothetical scenario with sample numbers)\n\n")
        readme.write("Leverage from a platform can be quantified in several ways. Here are some metrics that demonstrate the effectiveness of our TVP approach:\n\n")
        readme.write("1. **Developer Time Multiplication**: For every hour spent by the platform team, we save approximately 20 hours of development time across application teams.\n\n")
        readme.write("2. **Deployment Frequency**: Teams using our platform deploy 4x more frequently than teams managing their own infrastructure.\n\n")
        readme.write("3. **Onboarding Acceleration**: New developers become productive in 3 days versus 3 weeks without the platform.\n\n")
        readme.write("4. **Standardization Benefits**: Security audits take 70% less time due to consistent patterns and controls.\n\n")
        readme.write("5. **Cognitive Load Reduction**: Developers report spending 30% more time on business logic and 30% less time on infrastructure concerns.\n\n")
        readme.write("6. **Support Ratio**: Our platform team of 5 effectively supports 25 application teams (100+ developers).\n\n")
        readme.write("These metrics demonstrate the true leverage that comes from building a carefully designed Thinnest Viable Platform.\n\n")
        
        # Add a conclusion to tie everything together
        readme.write("## 11. Conclusion\n\n")
        readme.write("The diagrams and metrics presented above provide a comprehensive view of our Thinnest Viable Platform architecture ")
        readme.write("and the leverage it creates throughout the organization. ")
        readme.write("By implementing a GitOps approach with careful attention to component interaction and data flow, ")
        readme.write("we've created a platform that provides significant leverage through self-service APIs while maintaining simplicity and ease of use. ")
        readme.write("\n\n")
        readme.write("This platform embodies the TVP concept by offering just enough functionality to accelerate application teams ")
        readme.write("without the burden of unnecessary complexity. Just as a physical lever amplifies force, ")
        readme.write("our TVP amplifies the capabilities of both the platform team and development teams, ")
        readme.write("allowing the organization to achieve sublinear scaling while delivering more value to customers.\n\n")
        
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
