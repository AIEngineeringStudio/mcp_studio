# React and MCP App flow diagrams

Quick-reference diagrams extracted from `REACT_README.md`.

This flowchart emphasizes UI states, decisions, and error branches. For actor ownership, protocol boundaries, and
message order, see [`REACT_FLOW_SEQUENCE_DIAGRAM.md`](./REACT_FLOW_SEQUENCE_DIAGRAM.md).

## Connection boundaries

There are two separate connections:

```text
MCP App UI (inside an iframe)
        |
        | MCP Apps JSON-RPC over browser postMessage
        v
MCP host
        |
        | MCP protocol: tool and resource requests
        v
MCP server
```

The iframe UI connects to the host. It does not connect directly to the MCP server.

## Happy path

```text
1. React renders CustomerApp with customer = null.
2. useApp creates the MCP App object.
3. onAppCreated registers the toolresult listener.
4. useApp connects the iframe UI to the MCP host.
5. Host uses its MCP Client to ask the MCP Server to run get_customer().
6. MCP Server returns a tool result containing structuredContent.
7. Host sends the result to the iframe as a toolresult event.
8. The registered JavaScript handler validates result.structuredContent.
9. The handler calls setCustomer(data).
10. React calls CustomerApp again and updates the screen.
```

## Consolidated detailed flow

This diagram combines application startup, the MCP Apps handshake, tool execution, event timing, result validation,
React state changes, and every resulting UI state.

```mermaid
flowchart TD
    subgraph startup["1. Browser and React startup"]
        A["Browser loads index.html and App.jsx"] --> B["createRoot(...) renders CustomerApp<br/>inside #root"]
        B --> C["CustomerApp starts with<br/>customer = null<br/>resultError = null"]
    end

    subgraph setup["2. MCP App setup before connection"]
        C --> F["useApp creates the MCP App object"]
        F --> G["onAppCreated receives the App"]
        G --> H["Register the toolresult listener<br/>before connection"]
        H --> I["Only then, useApp calls app.connect()"]
    end

    subgraph handshake["3. UI-to-host connection handshake"]
        I --> J0["While connection is pending,<br/>React renders: Connecting to host..."]
        I --> J["Connect the PostMessageTransport"]
        J --> K["UI sends ui/initialize"]
        K --> L["Host returns capabilities and context"]
        L --> M["UI sends initialized notification"]
        M --> N{"Connection succeeds?"}
    end

    N -- "No" --> O["Store connection error"]
    O --> P["React renders<br/>Connection error"]
    N -- "Yes" --> Q["App is connected"]
    Q --> R["React renders<br/>Waiting for customer..."]

    subgraph execution["4. MCP tool execution"]
        Q --> S["Host uses its MCP Client to ask the<br/>MCP Server to run get_customer()"]
        S --> T["MCP Server runs get_customer()"]
        T --> U["Server returns a tool result containing<br/>structuredContent to the host"]
        U --> V["Host sends the result to the iframe<br/>as a toolresult event"]
    end

    subgraph handling["5. Result handling"]
        V --> Y["The registered JavaScript handler<br/>receives result"]
        Y --> Z{"result.isError?"}
        Z -- "Yes" --> AA["setResultError:<br/>The customer tool failed"]
        Z -- "No" --> AB["Read result.structuredContent"]
        AB --> AC{"Required UI fields valid?"}
        AC -- "No" --> AD["setResultError:<br/>The customer result has missing fields"]
        AC -- "Yes" --> AE["Clear resultError"]
        AE --> AF["Call setCustomer(data)"]
    end

    subgraph rendering["6. React state update and final UI"]
        AA --> AG["React re-renders"]
        AD --> AG
        AG --> AH["Render result error alert"]
        AF --> AI["React stores the customer and<br/>calls CustomerApp again"]
        AI --> AJ["CustomerApp returns customer JSX"]
        AJ --> AK["React updates the DOM"]
        AK --> AL["Customer fields appear:<br/>name, company, email, status"]
    end
```

### Why listener timing matters

```text
Safe:  register listener -> connect -> receive initial result
Risky: connect -> initial result arrives -> register listener too late
```

The diagram follows the safe order. `onAppCreated` installs the listener before `useApp` connects because the host may
send the initial result as soon as the connection is ready.

### Covered use cases

- Initial page and React startup
- MCP App creation and safe listener registration
- UI-to-host connection handshake
- Connection-pending UI
- Connection failure
- Connected UI waiting for a result
- Host-to-server tool execution and result delivery
- Exact `get_customer()` request and server execution responsibilities
- Correct listener timing and the missed-event risk
- Tool-reported failure
- Missing or invalid `structuredContent`
- `setCustomer(data)`, React re-rendering, DOM update, and successful customer display
