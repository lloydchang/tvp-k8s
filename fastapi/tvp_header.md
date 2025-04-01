---

# Thinnest Viable Platform (TVP) about Leverage

---

![This Lego experiment shows our brains prefer adding  Here's why it matters](https://github.com/user-attachments/assets/ea8b4c7f-bacc-4041-871b-8c1f85916e0c)
> - **To stabilize this roof, would you remove one block or add several blocks?**
>   - **Roof Image:**
>     - [**Nature Scientific Journal: _People systematically overlook subtractive changes_** by University of Virginia, Gabrielle Adams, Benjamin Converse, Andrew Hales and Leidy Klotz](https://www.nature.com/articles/s41586-021-03380-y#Fig5)
>       - [**World Economic Forum: _This Lego experiment shows our brains prefer adding. Here's why it matters_** by Harry Kretchmer](https://www.weforum.org/stories/2021/04/brains-prefer-adding-sustainability/)

# Backstory:

- [**Cloud Native Computing Foundation (CNCF) Platforms White Paper**](https://tag-app-delivery.cncf.io/whitepapers/platforms/)

> Inspired by the cross-functional cooperation promised by DevOps, platform engineering has begun to emerge in enterprises as an explicit form of that cooperation. Platforms **_curate_** and present foundational capabilities, frameworks and experiences to facilitate and accelerate the work of internal customers such as application developers, data scientists and information workers. Particularly in cloud computing, platforms have helped enterprises realize values long promised by the cloud like fast product releases, portability across infrastructures, more secure and resilient products, and greater developer productivity.

## Who is the audience?

> This paper intends to support enterprise leaders, enterprise architects and platform team leaders to advocate for, investigate and plan internal platforms for cloud computing. We believe platforms significantly impact enterprises' actual value streams, but only indirectly, so leadership consensus and support is vital to the long-term sustainability and success of platform teams. In this paper we'll enable that support by discussing what the value of platforms is, how to measure that value, and how to implement platform teams that maximize it.

## Why platforms?

> A team of platform experts not only reduces common work demanded of product teams but also optimizes platform capabilities used in those products. A platform team also maintains a set of conventional patterns, knowledge and tools used broadly across the enterprise; enabling developers to quickly contribute to other teams and products built on the same foundations. The shared platform patterns also allow embedding governance and controls in templates, patterns and capabilities. Finally, because platform teams corral providers and provide consistent experiences over their offerings, they enable efficient use of public clouds and service providers for foundational but undifferentiated capabilities such as databases, identity access, infrastructure operations, and app lifecycle.

## What is a Platform?

> A platform for cloud-native computing is an integrated collection of capabilities defined and presented according to the needs of the platform's users. It is a cross-cutting layer that ensures a consistent experience for acquiring and integrating typical capabilities and services for a broad set of applications and use cases. A good platform provides consistent user experiences for using and managing its capabilities and services, such as Web portals, project templates, and **_self-service APIs_**.

## Capabilities of Platforms:

> As we’ve described, a platform for cloud-native computing offers and composes capabilities and services from many supporting providers. These providers may be other teams within the same enterprise or third parties like cloud service providers. In a nutshell, platforms bridge from underlying capability providers to platform users like application developers; and in the process implement and enforce desired practices for security, performance, cost governance and consistent experience. The following graphic illustrates the relationships between products, platforms, and capability providers.

![Relationships between Products, Platforms, and Capability Providers](https://github.com/user-attachments/assets/be20e9ec-c203-451b-a954-c736e489a7d1)

> We've focused in this paper on how to construct a good platform and platform
team; now in this last section we'll describe the capabilities a platform may
actually offer. This list is intended to guide platform builders and includes
capabilities typically required by cloud-native applications. As we've noted
throughout though, a good platform reflects its users' needs, so ultimately
platform teams should choose and prioritize the capabilities their platform
offers together with its users.

> Capabilities may comprise several _features_, meaning aspects or attributes of
the parent capability's domain. For example, observability may include features
for gathering and publishing metrics, traces and logs as well as for observing
costs and energy consumption. Consider the need and priority for each feature or
aspect in your organization. Later CNCF publications may expand on each
domain further.

> Here are capability domains to consider when building platforms for cloud-native
computing:

> 1. **Web portals** for observing and provisioning products and capabilities
> 1. **APIs** (and CLIs) for automatically provisioning products and capabilities
> 1. **"Golden path" templates and docs** enabling optimal use of capabilities in products
> 1. **Automation for building and testing** services and products
> 1. **Automation for delivering and verifying** services and products
> 1. **Development environments** such as hosted IDEs and remote connection tools
> 1. **Observability** for services and products using instrumentation and
>    dashboards, including observation of functionality, performance and costs
> 1. **Infrastructure** services including compute runtimes, programmable
>    networks, and block and volume storage
> 1. **Data** services including databases, caches, and object stores
> 1. **Messaging** and event services including brokers, queues, and event fabrics
> 1. **Identity and secret** management services such as service and user identity
>    and authorization, certificate and key issuance, and static secret storage
> 1. **Security** services including static analysis of code and artifacts,
>    runtime analysis, and policy enforcement
> 1. **Artifact storage** including storage of container image and
   language-specific packages, custom binaries and libraries, and source code

> The following table is intended to help readers grasp each capability by loosely
> relating it to existing CNCF or CDF projects.

<table>
  <thead>
    <tr><td>Capability</td><td>Description</td><td>Example CNCF/CDF Projects</td></tr>
  </thead>
  <tr>
    <td>Web portals for provisioning and observing capabilities</td>
    <td>Publish documentation, service catalogs, and project templates. Publish telemetry about systems and capabilities.</td>
    <td>Backstage, Skooner, Ortelius</td>
  </tr>
  <tr>
    <td>APIs for automatically provisioning capabilities</td>
    <td>Structured formats for automatically creating, updating, deleting and observing capabilities.</td>
    <td>Kubernetes, Crossplane, Operator Framework, Helm, KubeVela</td>
  </tr>
  <tr>
    <td>Golden path templates and docs</td>
    <td>Templated compositions of well-integrated code and capabilities for rapid project development.</td>
    <td>ArtifactHub</td>
  </tr>
  <tr>
    <td>Automation for building and testing products</td>
    <td>Automate build and test of digital products and services.</td>
    <td>Tekton, Jenkins, Buildpacks, ko, Carvel</td>
  </tr>
  <tr>
    <td>Automation for delivering and verifying services</td>
    <td>Automate and observe delivery of services.</td>
    <td>Argo, Flux, Keptn, Flagger, OpenFeature</td>
  </tr>
  <tr>
    <td>Development environments</td>
    <td>Enable research and development of applications and systems.</td>
    <td>Devfile, Nocalhost, Telepresence, DevSpace</td>
  </tr>
  <tr>
    <td>Application observability</td>
    <td>Instrument applications, gather and analyze telemetry and publish info to stakeholders.</td>
    <td>OpenTelemetry, Jaeger, Prometheus, Thanos, Fluentd, Grafana, OpenCost, Pixie</td>
  </tr>
  <tr>
    <td>Infrastructure services</td>
    <td>Run application code, connect application components and persist data for applications</td>
    <td>Kubernetes, Kubevirt, Knative, WasmEdge, KEDA<br />CNI, Istio, Cilium, Envoy, Linkerd, CoreDNS<br />Rook, Longhorn, Etcd</td>
  </tr>
  <tr>
    <td>Data services</td>
    <td>Persist structured data for applications</td>
    <td>TiKV, Vitess, SchemaHero</td>
  </tr>
  <tr>
    <td>Messaging and event services</td>
    <td>Enable applications to communicate with each other asynchronously</td>
    <td>Strimzi, NATS, gRPC, Knative, Dapr</td>
  </tr>
  <tr>
    <td>Identity and secret services</td>
    <td>Ensure workloads have locators and secrets to use resources and capabilities. Enable services to identify themselves to other services</td>
    <td>Keycloak, Dex, External Secrets, SPIFFE/SPIRE, Teller, cert-manager</td>
  </tr>
  <tr>
    <td>Security services</td>
    <td>Observe runtime behavior and report/remediate anomalies. Verify builds and artifacts don't contain vulnerabilities. Constrain activities on the platform per enterprise requirements; notify and/or remediate aberrations</td>
    <td>Falco, In-toto, KubeArmor, OPA, Kyverno, Cloud Custodian</td>
  </tr>
  <tr>
    <td>Artifact storage </td>
    <td>Store, publish and secure built artifacts for use in production. Cache and analyze third-party artifacts. Store source code.</td>
    <td>ArtifactHub, Harbor, Distribution, Porter</td>
  </tr>
</table>

---

# Defining _Platform_ and Other Important Terms:

- [**O'Reilly: _Platform Engineering: A Guide for Technical, Product, and People Leaders_**](https://www.oreilly.com/library/view/platform-engineering/9781098153632/ch01.html) by [Camille Fournier](https://www.linkedin.com/in/camille-fournier-9011812/) and [Ian Nowland](https://www.linkedin.com/in/inowland/)

## Platform:

> We use [Evan Bottcher's definition from 2018](https://martinfowler.com/articles/talk-about-platforms.html), with a couple of terms updated. A platform is a foundation of **_self-service APIs_**, tools, services, knowledge, and support that are arranged as a **_compelling internal product_**. Autonomous application teams[1](https://www.oreilly.com/library/view/platform-engineering/9781098153632/ch01.html#id316) can make use of the platform to deliver **_product_** features at a higher pace, with reduced coordination.

> A corollary here is to ask: **what, then, _isn't_ a platform?** Well, for the purposes of this book, a platform requires you to be doing platform engineering. So, a wiki page isn't a platform, because there's no engineering to be done. "The cloud" also is not a platform by itself; you can bring cloud products together to create an internal platform, but on its own the cloud is an overwhelming array of offerings that is too large to be seen as a **_coherent platform_**.

## Platform Engineering:

> Platform engineering is the discipline of developing and operating platforms. The goal of this discipline is to manage overall system complexity in order to deliver **_leverage_** to the business. It does this by taking a **_curated product approach_** to developing platforms as software-based abstractions that serve a broad base of application developers, operating them as foundations of the business. We will elaborate on this in [Chapter 2](https://www.oreilly.com/library/view/platform-engineering/9781098153632/ch02.html#ch02_the_pillars_of_platform_engineering_1724889300873458).

## **_Leverage_**:

> Core to the value of platform engineering is the concept of **_leverage_**—meaning, the work of a few engineers on a platform team reduces the work of the greater organization. Platforms achieve **_leverage_** in two ways: making applications engineers more productive as they go about their jobs creating business value, and making the engineering organization more efficient by eliminating duplicate work across application engineering teams.

## Product:

> We believe that it is essential to **_view a platform as a product_**. Developing platforms as **_compelling products_** means that we take a customer-centric approach when deciding on the features of a platform. This implies a core focus on the users, but it requires more than just performatively hiring product managers and calling it a day. With the word "product" we strive to achieve for platforms what Steve Jobs created with Apple products: against a broad range of demand for features the product is deliberately and tastefully **_curated_**, both through what it does and, **_more importantly, through what it leaves out_**.

---

## Why Less Toil is Better:

- [**O'Reilly: _Site Reliability Engineering: How Google Runs Production Systems_**](https://sre.google/sre-book/eliminating-toil/) by [Jennifer Petoff](https://www.linkedin.com/in/jpetoff/), [Betsy Beyer](https://www.linkedin.com/in/betsy-beyer/), [Chris Jones](https://www.linkedin.com/in/chrisjonessre/) and [Niall Murphy](https://www.linkedin.com/in/niallm/)

> The work of reducing toil and scaling up services is the "Engineering" in Site Reliability Engineering. Engineering work is what enables the SRE organization to scale up **_sublinearly_** with service size and to manage services more efficiently than either a pure Dev team or a pure Ops team.

## **_Sublinear_** Scaling:

- [**USENIX SREcon: _Sublinear Scaling in Practice: The 1k SRE Project_**](https://www.usenix.org/conference/srecon19americas/presentation/rath) by [Nikolaus Rath](https://www.linkedin.com/in/nikolaus-rath-85342235/)

> At Google, one of the primary objectives of SRE teams is **_sublinear_** scaling: the size and number of SRE teams should grow more slowly than the number of supported services.

---

## What is a **_Thinnest_** Viable Platform (TVP)?

A TVP is a careful balance between keeping the platform small and ensuring that the platform is helping to accelerate and simplify software delivery for teams building on the platform. The concept was [introduced](https://teamtopologies.com/key-concepts-content/what-is-a-thinnest-viable-platform-tvp) by [Matthew Skelton](https://www.linkedin.com/in/matthewskelton/) and [Manuel Pais](https://www.linkedin.com/in/manuelpais/), co-authors of the book [_Team Topologies_](https://teamtopologies.com/book).

---

## Key Principles of TVP:

---

### Use modern software development techniques within the platform team:

#### [**Platform Engineering Maturity Model**](https://tag-app-delivery.cncf.io/whitepapers/platform-eng-maturity-model/):

> CNCF's initial [Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/) describes what internal platforms for cloud computing are and the values they promise to deliver to enterprises. But to achieve those values an organization must reflect and deliberately pursue outcomes and practices that are impactful for them, keeping in mind that every organization relies on an internal platform crafted for its own organization - even if that platform is just documentation on how to use third party services. This maturity model provides a framework for that reflection and for identifying opportunities for improvement in any organization.

#### How to use this model:

> As platform engineering has risen in prominence over the last few years, some patterns have become apparent. By organizing those patterns and observations into a progressive maturity model, we aim to orient [platform teams](https://tag-app-delivery.cncf.io/wgs/platforms/glossary/#platform-team) to the challenges they may face and opportunities to aim for. Each aspect is described by a continuum of characteristics of different teams and organizations at each level within the aspect. We expect readers to find themselves in the model and identify opportunities in adjacent levels.

> Of note, each additional level of maturity is accompanied by greater requirements for funding and people's time. Therefore, reaching the highest level should not be a goal in itself. Each level describes qualities that should appear at that stage. Readers must consider if their organization and their current context would benefit from these qualities given the required investment.

> Keep in mind that each aspect is meant to be evaluated and evolved independently. However, as in any socio-technical system these aspects are complex and interrelated. Thus you may find that to improve in one aspect you must reach a minimum level in another aspect too.

> It's also important to recognize that implementations of platforms vary from organization to organization. Make sure to evaluate the current state of _your_ group’s overall cloud native transformation. A phenomenal resource to leverage for this evaluation is the [Cloud Native Maturity Model](https://maturitymodel.cncf.io/).

> Finally, this model encourages organizations to mature their platform engineering discipline and their resulting platforms through intentional planning. Such planning and discipline themselves are a requirement for mature platform development and ongoing evolution.

> In general, keep in mind that mapping your organization into a model captures current state _to enable_ progressive iteration and improvement. [Martin Fowler](https://martinfowler.com/bliki/MaturityModel.html) says it well: "The true outcome of a maturity model assessment isn't what level you are at but the list of things you need to work on to improve. Your current level is merely a piece of intermediate work in order to determine that list of skills to acquire next." In that vein, seek to find yourself in the model then identify opportunities in adjacent levels.

#### Model table:

| <div style="width:120px">Aspect </div> |                                                                                            | Provisional            | Operational           | Scalable               | Optimizing                   |
|:---------------------------------------|:-------------------------------------------------------------------------------------------|:-----------------------|:----------------------|:-----------------------|:-----------------------------|
| [Investment](#Investment)     | _How are staff and funds allocated to platform capabilities?_                              | Voluntary or temporary | Dedicated team        | As product             | Enabled ecosystem            |
| [Adoption](#Adoption)         | _Why and how do users discover and use internal platforms and platform capabilities?_      | Erratic                | Extrinsic push        | Intrinsic pull         | Participatory                |
| [Interfaces](#Interfaces)     | _How do users interact with and consume platform capabilities?_                            | Custom processes       | Standard tooling      | Self-service solutions | Integrated services          |
| [Operations](#Operations)     | _How are platforms and their capabilities planned, prioritized, developed and maintained?_ | By request             | Centrally tracked     | Centrally enabled      | Managed services             |
| [Measurement](#Measurement)   | _What is the process for gathering and incorporating feedback and learning?_               | Ad hoc                 | Consistent collection | Insights               | Quantitative and qualitative |

---

### Focus on _Product Thinking_, viewing internal teams as customers
- [**DevOpsDays Melbourne**: Sprinkle your DevOps platform with **_Product Thinking_**](https://www.youtube.com/watch?v=rgV4HLSd1dk) by [Javier Turegano](https://www.linkedin.com/in/jturegano/) and [Leoren Tanyag Tesaluna](https://www.linkedin.com/in/leoren-tesaluna/)
- [**r/ProductManagement**: How applicable are Marty Cagan's thoughts on the real world?](https://www.reddit.com/r/ProductManagement/comments/1c5qztz/how_applicable_are_marty_cagan_thoughts_on_the/)

---

### Accelerate and simplify software delivery for teams using the platform
- [**r/ExperiencedDevs**: Curious what peoples experiences with Platform Teams are - what does your Platform Team do and how do they help other teams deliver?](https://www.reddit.com/r/ExperiencedDevs/comments/1dtwsij/curious_what_peoples_experiences_with_platform/)

---

### Build only what is _necessary_ - _Thinnest Viable_
- **Differentiate between customer wants and customer needs**
  - Customers may not always get what they want because it doesn't **_necessarily_** address their actual needs

---

As _Team Topologies_ [described](https://www.youtube.com/watch?v=8AQPSR09bxk):

> The interesting thing about platform is - it's maybe not the platforms of the past, because platforms of the past often in many organizations were great big great massive things; very difficult to use... The platforms we're talking about have placed a strong focus on developer experience; they see other development teams as their customers effectively.

### TVP Definition:

A **_Thinnest_** Viable Platform is the **_smallest set of APIs_**, documentation, and tools needed to accelerate the teams developing modern software services and systems.

### Examples of TVP:

- **A wiki page defining which cloud services to use and how to use them**
  - [A simple template for a wiki page for a TVP - as explained in the Team Topologies book](https://github.com/TeamTopologies/Thin-Platform-template)
  - [Examples of a TVP as defined in the book Team Topologies](https://github.com/TeamTopologies/Thinnest-Viable-Platform-examples)
  - [A TVP as described in Team Topologies, using just a Wiki page for a data platform](https://github.com/sbalnojan/TVP-example)
- **Documentation and tools focused on reducing cognitive load for development teams**
  - [Trade Me's Journey Towards a TVP](https://teamtopologies.com/industry-examples/trade-me-journey-towards-a-thinnest-viable-platform) by [Catherine Matheson](https://www.linkedin.com/in/catherine-matheson-31970b111/), [Amir Mohtasebi](https://www.linkedin.com/in/amirmohtasebi/) and [Eduardo da Silva](https://www.linkedin.com/in/emgsilva/)
  - [Cloud Native Operational Excellence (CNOE) is an open community collaboration with the goal of helping facilitate platform engineering through the sharing of guidance, tooling, and internal developer platform (IDP) reference architectures](https://cnoe.io/)
- **A _set of curated Application Programming Interfaces (APIs)_ with simplified access to infrastructure**
  - [Thinnest Viable Platform (TVP) about Leverage](https://github.com/lloydchang/tvp)

## System Architecture Documentation:

This [README.md](https://github.com/lloydchang/tvp/blob/main/README.md) provides a visual overview of the system architecture using various diagrams.
