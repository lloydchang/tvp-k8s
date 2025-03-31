# Thinnest Viable Platform (TVP)

## What is a TVP?

A TVP is a careful balance between keeping the platform small and ensuring that the platform is helping to accelerate and simplify software delivery for teams building on the platform. The concept was [introduced](https://teamtopologies.com/key-concepts-content/what-is-a-thinnest-viable-platform-tvp) by [Matthew Skelton](https://www.linkedin.com/in/matthewskelton/) and [Manuel Pais](https://www.linkedin.com/in/manuelpais/), co-authors of the book [_Team Topologies_](https://teamtopologies.com/book).

### Key Principles of TVP:

- **Use modern software development techniques within the platform team**
  - [**CNCF Platforms White Paper**](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
    > This paper intends to support enterprise leaders, enterprise architects and platform team leaders to advocate for, investigate and plan internal platforms for cloud computing. We believe platforms significantly impact enterprises’ actual value streams, but only indirectly, so leadership consensus and support is vital to the long-term sustainability and success of platform teams. In this paper we’ll enable that support by discussing what the value of platforms is, how to measure that value, and how to implement platform teams that maximize it.
  - [**Platform Engineering Maturity Model**](https://tag-app-delivery.cncf.io/whitepapers/platform-eng-maturity-model/)
    > CNCF’s initial [Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/) describes what internal platforms for cloud computing are and the values they promise to deliver to enterprises. But to achieve those values an organization must reflect and deliberately pursue outcomes and practices that are impactful for them, keeping in mind that every organization relies on an internal platform crafted for its own organization - even if that platform is just documentation on how to use third party services. This maturity model provides a framework for that reflection and for identifying opportunities for improvement in any organization.
- **Focus on _product thinking_, viewing internal teams as customers**
  - [Sprinkle your DevOps platform with **_product thinking_**](https://www.youtube.com/watch?v=rgV4HLSd1dk) by [Javier Turegano](https://www.linkedin.com/in/jturegano/) and [Leoren Tanyag Tesaluna](https://www.linkedin.com/in/leoren-tesaluna/)
  - [**r/ProductManagement**: How applicable are Marty Cagan thoughts on the real world](https://www.reddit.com/r/ProductManagement/comments/1c5qztz/how_applicable_are_marty_cagan_thoughts_on_the/)
- **Accelerate and simplify software delivery for teams using the platform**
  - [**r/ExperiencedDevs**: Curious what peoples experiences with Platform Teams are - what does your Platform Team do and how do they help other teams deliver?](https://www.reddit.com/r/ExperiencedDevs/comments/1dtwsij/curious_what_peoples_experiences_with_platform/)
- **Build only what is _necessary_ - "thinnest viable"**
  - **Differentiate between customer wants and customer needs**
    - Customers may not always get what they want because it doesn’t **_necessarily_** address their actual needs

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


## 1. Component Interaction Diagram

```mermaid
flowchart TB
    Client[Client Application] --> API[FastAPI Application]
    
    subgraph "FastAPI Application"
        API --> KR[Kubernetes Router]
        API --> AR[ArgoCD Router]
        API --> TR[TVP Router]
        API --> Health[Health Check]
        TR --> RT[Reconciliation Thread]
    end
    
    KR --> KC[Kubernetes Client]
    AR --> AT[ArgoCD Token]
    TR --> GitRepo[(Git Repository)]
    
    KC --> K8s[(Kubernetes API)]
    AT --> ArgoCD[(ArgoCD API)]
    RT --> GitRepo
    RT --> K8s
    
    classDef component fill:#f9f,stroke:#333,stroke-width:2px
    classDef api fill:#bbf,stroke:#33f,stroke-width:2px
    classDef external fill:#bfb,stroke:#3f3,stroke-width:2px
    
    class API,KR,AR,TR,Health component
    class KC,AT,RT api
    class K8s,ArgoCD,GitRepo external

```

## 2. API Structure Diagram

```mermaid
classDiagram
    class FastAPI {
        +title: str
        +description: str
        +version: str
        +startup_event()
        +root()
        +health_check()
    }
    
    class KubernetesRouter {
        +kubernetes_proxy()
        +get_kubernetes_client()
    }
    
    class ArgoCDRouter {
        +argocd_proxy()
        +get_argocd_token()
    }
    
    class TVPRouter {
        +get_tvp_status()
        +trigger_reconciliation()
        +get_deployment_status()
    }
    
    class Config {
        +Settings
        +get_settings()
        +get_kubernetes_client()
        +get_kubernetes_token()
    }
    
    FastAPI --> KubernetesRouter : includes
    FastAPI --> ArgoCDRouter : includes
    FastAPI --> TVPRouter : includes
    KubernetesRouter --> Config : depends on
    ArgoCDRouter --> Config : depends on
    TVPRouter --> Config : depends on
    FastAPI --> Config : depends on

```

## 3. ArgoCD Authentication Sequence

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant ArgoCDRouter
    participant Config
    participant ArgoCD
    
    Client->>FastAPI: Request to /argocd/...
    FastAPI->>ArgoCDRouter: Forward request
    ArgoCDRouter->>ArgoCDRouter: get_argocd_token()
    ArgoCDRouter->>Config: get_settings()
    Config-->>ArgoCDRouter: Returns settings
    
    ArgoCDRouter->>ArgoCD: POST /api/v1/session
    Note over ArgoCDRouter,ArgoCD: {username, password}
    ArgoCD-->>ArgoCDRouter: Authentication token
    
    ArgoCDRouter->>ArgoCD: Original request with token
    ArgoCD-->>ArgoCDRouter: Response data
    ArgoCDRouter-->>FastAPI: Formatted response
    FastAPI-->>Client: API response

```

## 4. Kubernetes Proxy Sequence

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant K8sRouter
    participant Config
    participant K8sAPI
    
    Client->>FastAPI: Request to /kubernetes/...
    FastAPI->>K8sRouter: Forward to kubernetes_proxy()
    K8sRouter->>Config: get_settings()
    Config-->>K8sRouter: Returns settings
    
    K8sRouter->>K8sRouter: Read K8s token from file
    K8sRouter->>K8sAPI: Proxied request with token
    K8sAPI-->>K8sRouter: JSON response
    K8sRouter-->>FastAPI: Formatted response
    FastAPI-->>Client: API response

```

## 5. TVP GitOps Reconciliation Sequence

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant TVPRouter
    participant ReconcileThread
    participant GitRepo
    participant K8sCluster
    
    Client->>FastAPI: POST /tvp/reconcile
    FastAPI->>TVPRouter: trigger_reconciliation()
    TVPRouter->>ReconcileThread: background_tasks.add_task(reconcile_from_git)
    TVPRouter-->>FastAPI: {"status": "started"}
    FastAPI-->>Client: Response
    
    ReconcileThread->>ReconcileThread: is_reconciling = true
    
    alt Repository doesn't exist
        ReconcileThread->>GitRepo: git clone
    else Repository exists
        ReconcileThread->>GitRepo: git fetch
        ReconcileThread->>GitRepo: git checkout branch
        ReconcileThread->>GitRepo: git pull
    end
    
    loop For each namespace/app
        ReconcileThread->>ReconcileThread: Read values.yaml
        ReconcileThread->>K8sCluster: Apply configuration
    end
    
    ReconcileThread->>ReconcileThread: Update last_reconciliation
    ReconcileThread->>ReconcileThread: is_reconciling = false

```

## 6. Health Check Sequence

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant K8sClient
    participant ArgoCD
    
    Client->>FastAPI: GET /health
    
    FastAPI->>K8sClient: list_namespace()
    alt K8s Healthy
        K8sClient-->>FastAPI: Success response
        FastAPI->>FastAPI: K8s status = "healthy"
    else K8s Unhealthy
        K8sClient-->>FastAPI: Error
        FastAPI->>FastAPI: K8s status = "unhealthy"
        FastAPI->>FastAPI: Overall status = "degraded"
    end
    
    FastAPI->>ArgoCD: get_argocd_token()
    alt ArgoCD Healthy
        ArgoCD-->>FastAPI: Valid token
        FastAPI->>FastAPI: ArgoCD status = "healthy"
    else ArgoCD Unhealthy
        ArgoCD-->>FastAPI: Error
        FastAPI->>FastAPI: ArgoCD status = "unhealthy"
        FastAPI->>FastAPI: Overall status = "degraded"
    end
    
    FastAPI-->>Client: Health status response

```

## 7. TVP GitOps Architecture

```mermaid
flowchart TB
    subgraph "Thinnest Viable Platform"
        API[FastAPI Application]
        RT[Reconciliation Thread]
        
        API --> RT
        RT --> API
    end
    
    Dev[Developers] -->|Git commit| GitRepo[(Git Repository)]
    GitRepo -->|Pull| RT
    RT -->|Apply configs| K8s[(Kubernetes Cluster)]
    
    subgraph "Kubernetes Cluster"
        K8s
        ArgoCD
    end
    
    Client[Client Application] --> API
    API -->|Proxy| K8s
    API -->|Proxy| ArgoCD
    
    classDef platform fill:#f9f,stroke:#333,stroke-width:2px
    classDef external fill:#bfb,stroke:#3f3,stroke-width:2px
    classDef user fill:#bbf,stroke:#33f,stroke-width:2px
    
    class API,RT platform
    class K8s,ArgoCD,GitRepo external
    class Dev,Client user

```

## 8. Application Deployment Workflow

```mermaid
stateDiagram-v2
    [*] --> GitRepoUpdate: Developer commits changes
    
    GitRepoUpdate --> Reconciliation: TVP periodic reconciliation
    GitRepoUpdate --> ManualReconcile: Manual trigger
    
    ManualReconcile --> Reconciliation
    
    Reconciliation --> ConfigReading: Read values.yaml
    ConfigReading --> ApplicationDeployment: Prepare deployment
    ApplicationDeployment --> ArgoCD: Create/Update ArgoCD application
    
    ArgoCD --> ApplicationSync: Auto-sync
    ArgoCD --> ManualSync: Manual sync
    
    ApplicationSync --> K8sDeployment
    ManualSync --> K8sDeployment
    
    K8sDeployment --> [*]: Application deployed
    
    state Reconciliation {
        [*] --> GitClone: First time
        [*] --> GitPull: Repository exists
        GitClone --> ProcessApps
        GitPull --> ProcessApps
        ProcessApps --> [*]
    }

```

## 9. Data Flow Diagram

```mermaid
flowchart TD
    User[User/Client] -->|API Request| API[FastAPI App]
    
    API -->|/kubernetes/*| KP[Kubernetes Proxy]
    API -->|/argocd/*| AP[ArgoCD Proxy]
    API -->|/tvp/*| TVP[TVP Router]
    
    KP -->|Auth token| KA[Kubernetes API]
    AP -->|Login| Auth[ArgoCD Auth]
    Auth -->|Token| AP
    AP -->|Auth token| AA[ArgoCD API]
    
    TVP -->|Status| TS[TVP Status]
    TVP -->|Reconcile| R[Reconciliation]
    
    TS --> Git[Git Repository]
    R --> Git
    R --> KA
    
    KA --> K8s[(Kubernetes Cluster)]
    AA --> ArgoCD[(ArgoCD Service)]
    
    classDef user fill:#bbf,stroke:#33f,stroke-width:2px
    classDef app fill:#f9f,stroke:#333,stroke-width:2px
    classDef external fill:#bfb,stroke:#3f3,stroke-width:2px
    
    class User user
    class API,KP,AP,TVP,TS,R,Auth app
    class K8s,ArgoCD,Git,KA,AA external

```

