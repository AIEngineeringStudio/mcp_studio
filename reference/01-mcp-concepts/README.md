# Learn MCP progressively

This course contains **32 numbered concept guides**, plus a beginner orientation
and a few clearly labeled supplemental comparisons. Begin with one ordinary
Python ticket lookup, expose it through MCP, then add process, network,
security, and operational boundaries only as requirements grow.

The initial guides need no installation. Basic Python is useful for the
hands-on labs, which need no Docker, database, model account, or API key.
Each guide states its outcome and prerequisites, explains the mechanism,
traces examples and failures, and links to original sources.

## Start here if MCP is new to you

Read [the beginner mental model](guides/00-intro.md) before concept 01. It
defines host, model, client, server, tool, resource, prompt, JSON-RPC, and
transport using one small example. No installation is required.

Each foundational guide follows the same learning pattern:

1. start with the user need or ordinary Python behavior;
2. define each new term before using it;
3. show one small visual flow;
4. follow with a concrete code or message example;
5. separate what the example proves from what production still requires.

Do not try to memorize the entire protocol. On a first pass, complete concepts
00 through 07 and run the in-memory lab. Return to process, HTTP, security, and
operations when you need those boundaries.

## How to use the course

Follow the numbered path for a first pass. For a targeted question, open the
relevant guide and follow only its prerequisite links. Optional experiments
demonstrate software behavior; there are no required quizzes.

Start [lab setup](fast-mcp-2026-07-28/labs/README.md) at guide 07. Check
[versions and compatibility](VERSIONS.md) before comparing wire messages.
The [validation record](VALIDATION.md) states which examples actually ran.

Ask the tutor: `Teach me concept 01`, `Continue`, `Go deeper into dispatch`,
`Build the stdio example`, or `Show the full production evolution`.
These numbers identify course concepts, not AI curriculum cases.

## Stage A: understand and prove the core boundary

1. [Why MCP exists](guides/01-why-mcp.md)
   Explain the integration problem MCP solves and when a direct function is
   sufficient.

2. [Host, client, model, and server](guides/02-host-client-server.md)
   Locate each participant and assign responsibility for one tool invocation.

3. [JSON-RPC requests, responses, and notifications](guides/03-json-rpc.md)
   Read a message envelope and distinguish request identity from business
   identity.

4. [Protocol versions and capability discovery](guides/04-versions-discovery.md)
   Explain modern request metadata and recognize a legacy initialization trace.

5. [Tools and their contracts](guides/05-tool-contracts.md)
   Design a narrow tool with a clear input, result, side effect, and failure
   contract.

   Optional references after concept 05:

    - [Compare tools, resources, and prompts](guides/05C-mcp-primitives.md)
    - [Legacy stateful lifecycle through 2025-11-25](guides/05A-stateful-lifecycle.md)
    - [Modern stateless-first lifecycle in 2026-07-28](guides/05B-stateless-lifecycle.md)

   The lifecycle references are detailed compatibility material. They are not
   prerequisites for writing the first tool.

6. [FastMCP registration and dispatch](guides/06-fastmcp-registry.md)
   Trace how a Python function becomes a discoverable MCP tool.

7. [The first client and in-memory testing](guides/07-in-memory-client.md)
   Run a deterministic MCP interaction without an LLM or a network service.

8. [stdio and subprocess boundaries](guides/08-stdio-processes.md)
   Run the same service in a child process and explain stdin, stdout, and
   stderr.

9. [Resources, URIs, and templates](guides/09-resources.md)
   Represent readable context with a URI and distinguish resource reads from
   tool actions.

10. [Reusable MCP prompts](guides/10-prompts.md)
    Retrieve a parameterized prompt and explain why retrieval does not run a
    model.

## Stage B: network behavior and application ownership

11. [Streamable HTTP](guides/11-streamable-http.md)
    Move a working MCP contract across a network and recognize modern HTTP
    behavior.

12. [Progress, streaming, and final results](guides/12-progress-streaming.md)
    Distinguish work progress from returned data, SSE framing, and model-token
    streaming.

13. [Elicitation and additional user input](guides/13-elicitation.md)
    Explain how an MCP operation obtains missing information without inventing a
    user's answer.

14. [Continuation state and safe reentry](guides/14-continuation-state.md)
    Preserve a multi-round operation's context without trusting
    client-controlled state.

15. [Async I/O and concurrent requests](guides/15-async-concurrency.md)
    Explain where async helps and why shared mutable state needs a separate
    design.

16. [Service layers and persistence](guides/16-service-persistence.md)
    Separate MCP translation from business rules and durable storage.

17. [Application lifespan and dependency ownership](guides/17-application-lifespan.md)
    Assign startup and shutdown responsibility for shared dependencies.

18. [Uvicorn, workers, and process state](guides/18-process-runtime.md)
    Separate the HTTP runtime from the application and reason about multiple
    workers.

## Stage C: secure and deploy the service

19. [Host validation, Origin, and CORS](guides/19-origin-cors.md)
    Explain what browser-related transport checks protect and why they are not
    authentication.

20. [OAuth discovery and delegated calendar access](guides/20-oauth-discovery.md)
    Trace how a client finds the authorization server for a protected MCP
    resource
    and keeps an MCP token separate from a downstream calendar credential.

21. [Authorization, tool visibility, and calendar isolation](guides/21-authorization.md)
    Enforce who can discover and call calendar tools, then apply user, tenant,
    record, and downstream-provider policy.

22. [Reverse proxies and TLS](guides/22-proxy-tls.md)
    Explain where a proxy sits and diagnose route, trust, and buffering
    failures.

23. [Configuration and reproducible environments](guides/23-configuration.md)
    Separate configuration from code and validate required production settings
    at startup.

24. [Docker packaging and networking](guides/24-containers.md)
    Explain image, container, network, and volume boundaries without confusing
    them with MCP.

## Stage D: reliability, operations, and compatibility

25. [Timeouts, cancellation, retries, and idempotency](guides/25-reliability.md)
    Design a retry policy around operation outcomes rather than connection
    symptoms.

26. [Pagination, caching, and subscriptions](guides/26-pagination-cache.md)
    Keep large catalogs and resources bounded, fresh, and isolated by caller.

27. [Testing and debugging MCP by layer](guides/27-testing.md)
    Choose checks that isolate the failing boundary and prove the intended
    behavior.

28. [Logs, metrics, and traces](guides/28-observability.md)
    Select operational evidence that explains a slow or failed tool call.

29. [Scaling and MCP gateways](guides/29-scaling-gateways.md)
    Add routing and shared infrastructure only when requirements justify their
    cost.

30. [Optional extensions and deprecated features](guides/30-extensions.md)
    Separate core MCP from Apps, Tasks, Skills, and compatibility-only features.

31. [Reading and migrating legacy MCP examples](guides/31-legacy-migration.md)
    Identify an archived example's protocol and framework before adapting it.

32. [A ticket service grown one requirement at a time](guides/32-capstone.md)
    Connect the individual concepts into a staged implementation with explicit
    evidence.

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

- [Machine-readable curriculum](../curriculum.json)
- [Teaching skill](../../.agents/mcp-progressive-tutor/SKILL.md)

The original collection is preserved as source material in the adjacent
`fast-mcp`, `fastMcp-fastApi-uvicorn-ngnix-docker`, `streamable`, `12-auth`
folders.

The workspace teaching skill is
[mcp-progressive-tutor](../../.agents/mcp-progressive-tutor/SKILL.md).
Ask, for example, `Use mcp-progressive-tutor to teach me MCP from basics`,
`Continue`, or `Explain concept 13 in more depth`.

## How to maintain this library

Maintain each concept in its individual guide. Link to that guide when another
lesson depends on it. Preserve transcripts for provenance; adding another
transcript does not automatically change the course.

When adding references, review the new material, update the affected source
links, and revise only the relevant guides. Check the
[version baseline](VERSIONS.md) before changing examples. Protocol revisions
and framework versions are different version numbers.

**Review boundary:**

> The curated course and synthetic labs are maintained separately from the
> archived source material. An archived explanation is not a correctness
> certification. Use the current concept guides, version baseline, and
> validation record when deciding what to implement.
