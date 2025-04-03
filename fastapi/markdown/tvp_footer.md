---

# Appendix

---

# Measurement Frameworks:

---

## [SRE: The Four Golden Signals of Site Reliablity Engineering](https://sre.google/sre-book/monitoring-distributed-systems/#xref_monitoring_golden-signals)

> **The Four Golden Signals**
> 
> The four golden signals of monitoring are latency, traffic, errors, and saturation. If you can only measure four metrics of your user-facing system, focus on these four.
> 
> **Latency**
> 
> - The time it takes to service a request. It’s important to distinguish between the latency of successful requests and the latency of failed requests. For example, an HTTP 500 error triggered due to loss of connection to a database or other critical backend might be served very quickly; however, as an HTTP 500 error indicates a failed request, factoring 500s into your overall latency might result in misleading calculations. On the other hand, a slow error is even worse than a fast error! Therefore, it’s important to track error latency, as opposed to just filtering out errors.
> 
> **Traffic**
> 
> - A measure of how much demand is being placed on your system, measured in a high-level system-specific metric. For a web service, this measurement is usually HTTP requests per second, perhaps broken out by the nature of the requests (e.g., static versus dynamic content). For an audio streaming system, this measurement might focus on network I/O rate or concurrent sessions. For a key-value storage system, this measurement might be transactions and retrievals per second.
> 
> **Errors**
> 
> - The rate of requests that fail, either explicitly (e.g., HTTP 500s), implicitly (for example, an HTTP 200 success response, but coupled with the wrong content), or by policy (for example, "If you committed to one-second response times, any request over one second is an error"). Where protocol response codes are insufficient to express all failure conditions, secondary (internal) protocols may be necessary to track partial failure modes. Monitoring these cases can be drastically different: catching HTTP 500s at your load balancer can do a decent job of catching all completely failed requests, while only end-to-end system tests can detect that you’re serving the wrong content.
> 
> **Saturation**
> 
> - How "full" your service is. A measure of your system fraction, emphasizing the resources that are most constrained (e.g., in a memory-constrained system, show memory; in an I/O-constrained system, show I/O). Note that many systems degrade in performance before they achieve 100% utilization, so having a utilization target is essential.
> 
> - In complex systems, saturation can be supplemented with higher-level load measurement: can your service properly handle double the traffic, handle only 10% more traffic, or handle even less traffic than it currently receives? For very simple services that have no parameters that alter the complexity of the request (e.g., "Give me a nonce" or "I need a globally unique monotonic integer") that rarely change configuration, a static value from a load test might be adequate. As discussed in the previous paragraph, however, most services need to use indirect signals like CPU utilization or network bandwidth that have a known upper bound. Latency increases are often a leading indicator of saturation. Measuring your 99th percentile response time over some small window (e.g., one minute) can give a very early signal of saturation.
> 
> - Finally, saturation is also concerned with predictions of impending saturation, such as "It looks like your database will fill its hard drive in 4 hours."
> 
> If you measure all four golden signals and page a human when one signal is problematic (or, in the case of saturation, nearly problematic), your service will be at least decently covered by monitoring.

---

## [DORA: Core Model of DevOps Research and Assessment](https://dora.dev/research/?view=detail)

![dora-core-v2 0 0-detail](https://github.com/user-attachments/assets/dddac594-7f4a-40de-9701-7e725fa51605)

---

## [The SPACE of Developer Productivity: There's more to it than you think](https://queue.acm.org/detail.cfm?id=3454124)

![1_PgPlUhNagdK9mrj97gOG3g](https://github.com/user-attachments/assets/bd48b91d-2c86-49fd-b19b-8caf55ea9907)

---

## [DevEx: What Actually Drives Productivity: The developer-centric approach to measuring and improving productivity](https://queue.acm.org/detail.cfm?id=3595878)

![noda-table1](https://github.com/user-attachments/assets/9a3c1929-59b7-4d4d-b0ba-f74931207808)

---

## [PULSE and HEART: Measuring the User Experience on a Large Scale: User-Centered Metrics for Web Applications](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/)

> More and more products and services are being deployed
on the web, and this presents new challenges and
opportunities for measurement of user experience on a large
scale. There is a strong need for user-centered metrics for
web applications, which can be used to measure progress
towards key goals, and drive product decisions. In this
note, we describe the HEART framework for user-centered
metrics, as well as a process for mapping product goals to
metrics. We include practical examples of how HEART
metrics have helped product teams make decisions that are
both data-driven and user-centered. The framework and
process have generalized to enough of our company’s own
products that we are confident that teams in other
organizations will be able to reuse or adapt them. We also
hope to encourage more research into metrics based on
large-scale behavioral data.

> **PULSE METRICS**
> The most commonly used large-scale metrics are focused
on business or technical aspects of a product, and they (or
similar variations) are widely used by many organizations
to track overall product health. We call these PULSE
metrics:

> **P**age views,

> **U**ptime,

> **L**atency,

> **S**even-day active users (i.e. the number of unique users who used the product
at least once in the last week), and

> **E**arnings.

> **HEART METRICS**
> Based on the shortcomings we saw in PULSE, both for
measuring user experience quality, and providing
actionable data, we created a complementary metrics
framework, HEART:

> **H**appiness,

> **E**ngagement,

> **A**doption,

> **R**etention, and

> **T**ask success.

> These are categories, from
which teams can then define the specific metrics that they
will use to track progress towards goals. The Happiness and
Task Success categories are generalized from existing user
experience metrics: Happiness incorporates satisfaction,
and Task Success incorporates both effectiveness and
efficiency. Engagement, Adoption, and Retention are new
categories, made possible by large-scale behavioral data. 

---

## [CASTLE: A UX Framework for Workplace Software](https://www.nngroup.com/articles/castle-framework/)

> The HEART framework is great for B2C products but is lacking for workplace applications where users cannot choose the product. CASTLE offers a complementary assessment framework for UX that focuses on the needs of internal product teams.

> CASTLE is an acronym for:

> C = Cognitive load

> A = Advanced feature usage

> S = Satisfaction

> T = Task efficiency

> L = Learnability

> E = Errors

> Much like in the HEART framework, the six dimensions are constructs intended to represent the most important elements of user experience for productivity applications that are used as part of someone’s job. The selection of these constructs has taken into account general user-experience principles and priorities, as well as typical business cases and needs for workplace software.

---

# Trade Me's Journey Towards a TVP

## Just big enough
 
> TVP intends to ensure the absolute minimum requirements we expect from our production systems are implemented and abstracted away from our developers. This way, we keep the platform as simple as possible to cater to one of its primary purposes: reducing developers’ cognitive load. As the “Thinnest” in the abbreviation implies, it is just big enough. We look at parts of systems that are common across all domains. For example, every system needs monitoring. We provide this out of the box with TVP, so developers don’t need to remember to add monitoring when creating a new service; it’s automatically provided with our chosen monitoring tool. 

![Trade Me's Journey Towards a TVP](https://github.com/user-attachments/assets/219f1493-a404-45b0-8918-3a10c45e6455)

> The diagram above is a simplified version of how teams interact with the TVP.  We have three stream-aligned teams that work on the platform. Stream-aligned teams from Consumer & Marketplace and Classifieds use a TVP to build their new services. The team that owns TVP will provide support for TVP’s users, and will continually improve the TVP user experience based on feedback with pushed updates. The process and experience resembles that of any third-party software, except all done internally. 

---

# Analogies:

---

## Levers: What Makes Things Move?

---

> A [lever](https://en.wikipedia.org/wiki/Lever) amplifies an input force to provide a greater output force, which is said to provide [**_leverage_**](https://en.wikipedia.org/wiki/Leverage), which is [mechanical advantage](https://en.wikipedia.org/wiki/Mechanical_advantage) gained in the system, equal to the ratio of the output force to the input force.

> A [lever](https://www.oocities.org/rjwarren_stm/College_Physics/Mechanical_Systems.html) consists of a rigid bar that can rotate about a fixed point called a fulcrum.

> [Depending](https://teachersinstitute.yale.edu/curriculum/units/2014/4/14.04.04/2) on the positions of fulcrum, input force and applied force, one can define three types of levers: first class, second class and third class.

![First Class Lever](https://github.com/user-attachments/assets/32435cde-aac8-4cf9-a902-2146977d2d8b)

![Second Class Lever](https://github.com/user-attachments/assets/e425a6a8-49f9-4fd9-b7fb-34944ab9cfa5)

![Third Class Lever](https://github.com/user-attachments/assets/cb60a23f-d5dc-44a7-a099-6b16e482f4e0)
