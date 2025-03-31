# Thinnest Viable Platform (TVP)

## What is a TVP?

A TVP is a careful balance between keeping the platform small and ensuring that the platform is helping to accelerate and simplify software delivery for teams building on the platform. The concept was [introduced](https://teamtopologies.com/key-concepts-content/what-is-a-thinnest-viable-platform-tvp) by [Matthew Skelton](https://www.linkedin.com/in/matthewskelton/) and [Manuel Pais](https://www.linkedin.com/in/manuelpais/), co-authors of the book [_Team Topologies_](https://teamtopologies.com/book).

### Key Principles of TVP:

- **Use modern software development techniques within the platform team**
  - [CNCF Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
    > This paper intends to support enterprise leaders, enterprise architects and platform team leaders to advocate for, investigate and plan internal platforms for cloud computing. We believe platforms significantly impact enterprises’ actual value streams, but only indirectly, so leadership consensus and support is vital to the long-term sustainability and success of platform teams. In this paper we’ll enable that support by discussing what the value of platforms is, how to measure that value, and how to implement platform teams that maximize it.
  - [Platform Engineering Maturity Model](https://tag-app-delivery.cncf.io/whitepapers/platform-eng-maturity-model/)
    > CNCF’s initial [Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/) describes what internal platforms for cloud computing are and the values they promise to deliver to enterprises. But to achieve those values an organization must reflect and deliberately pursue outcomes and practices that are impactful for them, keeping in mind that every organization relies on an internal platform crafted for its own organization - even if that platform is just documentation on how to use third party services. This maturity model provides a framework for that reflection and for identifying opportunities for improvement in any organization.
- **Focus on _product thinking_, viewing internal teams as customers**
  - [Sprinkle your DevOps platform with _product thinking_](https://www.youtube.com/watch?v=rgV4HLSd1dk) by [Javier Turegano](https://www.linkedin.com/in/jturegano/) and [Leoren Tanyag Tesaluna](https://www.linkedin.com/in/leoren-tesaluna/)
- **Accelerate and simplify software delivery for teams using the platform**
  - [r/ExperiencedDevs: Curious what peoples experiences with Platform Teams are - what does your Platform Team do and how do they help other teams deliver?](https://www.reddit.com/r/ExperiencedDevs/comments/1dtwsij/curious_what_peoples_experiences_with_platform/)
- **Build only what is _necessary_ - "thinnest viable"**
  - Differentiate between customer needs and customer wants
    - Customers may not always get what they want because it doesn’t _necessarily_ address their actual needs

As Matthew Skelton [explains](https://www.youtube.com/watch?v=8AQPSR09bxk):

> The interesting thing about platform is - it's maybe not the platform's of the past, because platforms of the past often in many organizations were great big great massive things, very difficult to use... The platforms we're talking about have placed a strong focus on developer experience, they see other development teams as their customers effectively.

### TVP Definition:

A Thinnest Viable Platform is the smallest set of APIs, documentation, and tools needed to accelerate the teams developing modern software services and systems.

### Examples of TVP:

- A wiki page defining which cloud services to use and how to use them
  - https://github.com/TeamTopologies/Thin-Platform-template
  - https://github.com/TeamTopologies/Thinnest-Viable-Platform-examples
  - https://github.com/sbalnojan/TVP-example
- Documentation and tools focused on reducing cognitive load for development teams
  - https://teamtopologies.com/industry-examples/trade-me-journey-towards-a-thinnest-viable-platform
  - https://cnoe.io/
    - https://github.com/cnoe-io/idpbuilder
  - https://github.com/backstage/backstage
    - https://github.com/backstage
  - https://roadie.io/
  - https://www.atlassian.com/software/compass
- A set of curated APIs with simplified access to infrastructure
  - https://github.com/lloydchang/tvp

## System Architecture Documentation

This [README.md](https://github.com/lloydchang/tvp/blob/main/README.md) provides a visual overview of the system architecture using various diagrams.
