# Architecture

```
user prompt
    │
    ▼
ToolCallingAgent ─── AgentModel adapter
    │                      ▲
    │ MCP tool call        │ observation
    ▼                      │
ObservedMCPClient ─ semantic client record
    │
    ├── stdio wiretap ─ exact JSON-RPC lines
    │        │
    │        ▼
    └── Streamable HTTP ─ HTTP body recorder
             │
             ▼
          MCPServer ─ semantic server middleware
             ├── tools
             ├── resources
             └── prompts
```

The core agent depends on two small protocols: a model and a tool gateway. This
makes the decision loop testable without a network or paid model API. MCP is one
tool gateway implementation.

The raw recorders are transport-specific because stdio framing and HTTP framing
are different. Client facade and server middleware records are transport-neutral.

This is a learning repository, not a ready-made security boundary. Production
work needs authentication, authorization, request limits, domain-specific
redaction, retention controls, sampling, and strict command allowlists.

