# Learn MCP progressively

This course contains **32 individual concept guides**. Begin with a ticket
lookup, expose it through MCP, then add process, network, security, and
operational boundaries as requirements grow.

The initial guides need no installation. Basic Python is useful for the
hands-on labs, which need no Docker, database, model account, or API key.
Each guide states its outcome and prerequisites, explains the mechanism,
traces examples and failures, and links to original sources.

## How to use the course

Follow the numbered path for a first pass. For a targeted question, open the
relevant guide and follow only its prerequisite links. Optional experiments
demonstrate software behavior; there are no required quizzes.

Start [lab setup](labs/README.md) at guide 07. Check
[versions and compatibility](VERSIONS.md) before comparing wire messages.
The [validation record](VALIDATION.md) states which examples actually ran.

Ask the tutor: `Teach me concept 01`, `Continue`, `Go deeper into dispatch`,
`Build the stdio example`, or `Show the full production evolution`.
These numbers identify course concepts, not AI curriculum cases.

## Stage A: understand and prove the core boundary

1. [Why MCP exists](concepts/01-why-mcp.md)
   Explain the integration problem MCP solves and when a direct function is sufficient.

2. [Host, client, model, and server](concepts/02-host-client-server.md)
   Locate each participant and assign responsibility for one tool invocation.

3. [JSON-RPC requests, responses, and notifications](concepts/03-json-rpc.md)
   Read a message envelope and distinguish request identity from business identity.

4. [Protocol versions and capability discovery](concepts/04-versions-discovery.md)
   Explain modern request metadata and recognize a legacy initialization trace.

5. [Tools and their contracts](concepts/05-tool-contracts.md)
   Design a narrow tool with a clear input, result, side effect, and failure contract.

6. [FastMCP registration and dispatch](concepts/06-fastmcp-registry.md)
   Trace how a Python function becomes a discoverable MCP tool.

7. [The first client and in-memory testing](concepts/07-in-memory-client.md)
   Run a deterministic MCP interaction without an LLM or a network service.

8. [stdio and subprocess boundaries](concepts/08-stdio-processes.md)
   Run the same service in a child process and explain stdin, stdout, and stderr.

9. [Resources, URIs, and templates](concepts/09-resources.md)
   Represent readable context with a URI and distinguish resource reads from tool actions.

10. [Reusable MCP prompts](concepts/10-prompts.md)
   Retrieve a parameterized prompt and explain why retrieval does not run a model.

## Stage B: network behavior and application ownership

11. [Streamable HTTP](concepts/11-streamable-http.md)
   Move a working MCP contract across a network and recognize modern HTTP behavior.

12. [Progress, streaming, and final results](concepts/12-progress-streaming.md)
   Distinguish work progress from returned data, SSE framing, and model-token streaming.

13. [Elicitation and additional user input](concepts/13-elicitation.md)
   Explain how an MCP operation obtains missing information without inventing a user's answer.

14. [Continuation state and safe reentry](concepts/14-continuation-state.md)
   Preserve a multi-round operation's context without trusting client-controlled state.

15. [Async I/O and concurrent requests](concepts/15-async-concurrency.md)
   Explain where async helps and why shared mutable state needs a separate design.

16. [Service layers and persistence](concepts/16-service-persistence.md)
   Separate MCP translation from business rules and durable storage.

17. [Application lifespan and dependency ownership](concepts/17-application-lifespan.md)
   Assign startup and shutdown responsibility for shared dependencies.

18. [Uvicorn, workers, and process state](concepts/18-process-runtime.md)
   Separate the HTTP runtime from the application and reason about multiple workers.

## Stage C: secure and deploy the service

19. [Host validation, Origin, and CORS](concepts/19-origin-cors.md)
   Explain what browser-related transport checks protect and why they are not authentication.

20. [OAuth discovery and delegated calendar access](concepts/20-oauth-discovery.md)
   Trace how a client finds the authorization server for a protected MCP resource
   and keeps an MCP token separate from a downstream calendar credential.

21. [Authorization, tool visibility, and calendar isolation](concepts/21-authorization.md)
   Enforce who can discover and call calendar tools, then apply user, tenant,
   record, and downstream-provider policy.

22. [Reverse proxies and TLS](concepts/22-proxy-tls.md)
   Explain where a proxy sits and diagnose route, trust, and buffering failures.

23. [Configuration and reproducible environments](concepts/23-configuration.md)
   Separate configuration from code and validate required production settings at startup.

24. [Docker packaging and networking](concepts/24-containers.md)
   Explain image, container, network, and volume boundaries without confusing them with MCP.

## Stage D: reliability, operations, and compatibility

25. [Timeouts, cancellation, retries, and idempotency](concepts/25-reliability.md)
   Design a retry policy around operation outcomes rather than connection symptoms.

26. [Pagination, caching, and subscriptions](concepts/26-pagination-cache.md)
   Keep large catalogs and resources bounded, fresh, and isolated by caller.

27. [Testing and debugging MCP by layer](concepts/27-testing.md)
   Choose checks that isolate the failing boundary and prove the intended behavior.

28. [Logs, metrics, and traces](concepts/28-observability.md)
   Select operational evidence that explains a slow or failed tool call.

29. [Scaling and MCP gateways](concepts/29-scaling-gateways.md)
   Add routing and shared infrastructure only when requirements justify their cost.

30. [Optional extensions and deprecated features](concepts/30-extensions.md)
   Separate core MCP from Apps, Tasks, Skills, and compatibility-only features.

31. [Reading and migrating legacy MCP examples](concepts/31-legacy-migration.md)
   Identify an archived example's protocol and framework before adapting it.

32. [A ticket service grown one requirement at a time](concepts/32-capstone.md)
   Connect the individual concepts into a staged implementation with explicit evidence.

## Practical milestones and maintenance

The supplied lab demonstrates tools, resources, and prompts through memory,
stdio, and HTTP. A separate domain model demonstrates approval and replay.
The calendar authorization lab demonstrates Protected Resource Metadata,
scope-filtered tool discovery, direct-call enforcement, and a mock downstream
credential broker without using real accounts or secrets.
Production chapters contain worked design explanations; they are not
prebuilt deployments. The capstone provides the implementation progression.

Maintain one guide per concept and link back to prerequisites rather than
copying them. Before adopting a new transcript, review its protocol era,
sources, and examples, then revise only the affected guides.

- [Machine-readable curriculum](curriculum.json)
- [Teaching skill](../../.agents/mcp-progressive-tutor/SKILL.md)

The original collection is preserved as source material. Use the
[review and source map](catalog/REVIEW.md) to understand which sources are
useful and which need correction. 

The workspace teaching skill is
[mcp-progressive-tutor](../../.agents/mcp-progressive-tutor/SKILL.md).
Ask, for example, `Use mcp-progressive-tutor to teach me MCP from basics`,
`Continue`, or `Explain concept 13 in more depth`.


## How to maintain this library

Maintain each concept in its individual guide. Link to that guide when another
lesson depends on it. Preserve transcripts for provenance; adding another
transcript does not automatically change the course.

When adding references, run this command from the workspace root:

```bash
python3 reference/mcp/catalog/build_catalog.py
```

Then review the new material, update the source map, and revise only the
affected guides. The generator updates the inventory, not the curated lessons.
Check the [version baseline](VERSIONS.md) before changing examples.
Protocol revisions and framework versions are different version numbers.

**Review boundary:**

> The catalog covers every original file. Text was scanned in full for inventory
> and overlap analysis, then reviewed structurally and thematically with selected
> close reading. It is not a line-by-line correctness certification of every
> archived example. Archived programs and visual assets remain unverified unless
> a review note explicitly says otherwise.
