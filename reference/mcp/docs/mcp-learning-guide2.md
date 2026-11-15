# MCP Learning Guide
## Transaction Search Agent - Focus on MCP + UI

───────────────────────────────────────────────────────────────────────────────
## 1. WHAT IS MCP?
───────────────────────────────────────────────────────────────────────────────

### 1.1 Definition

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MCP = Model Context Protocol                                               │
│                                                                             │
│  A standard way for AI agents to call external tools.                       │
│                                                                             │
│  Think of it as:                                                            │
│  • A "USB port" for AI — plug in any tool                                   │
│  • A contract between AI and tools                                          │
│  • Language-agnostic protocol (works with any programming language)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Why MCP Matters

```
WITHOUT MCP:                          WITH MCP:
─────────────────────────────────     ─────────────────────────────────
• Custom integration per tool         • Standard interface for all tools
• Tight coupling                      • Loose coupling
• Hard to swap tools                  • Easy to add/remove tools
• Vendor lock-in                      • Interoperability
```

### 1.3 MCP in This Project

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   User: "Show high-risk transactions"                                       │
│                     │                                                       │
│                     ▼                                                       │
│              ┌─────────────┐                                                │
│              │  AI Agent   │  ← Decides: "I need to search transactions"   │
│              └──────┬──────┘                                                │
│                     │                                                       │
│                     ▼                                                       │
│              ┌─────────────┐                                                │
│              │   Gateway   │  ← Routes tool call                            │
│              └──────┬──────┘                                                │
│                     │                                                       │
│                     ▼  MCP Protocol                                         │
│              ┌─────────────┐                                                │
│              │ MCP Server  │  ← Executes tool, returns data                 │
│              │ (Tools)     │                                                │
│              └─────────────┘                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

───────────────────────────────────────────────────────────────────────────────
## 2. MCP CORE CONCEPTS
───────────────────────────────────────────────────────────────────────────────

### 2.1 Key Terms

```
┌─────────────────┬──────────────────────────────────────────────────────────┐
│ TERM            │ MEANING                                                  │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ MCP Server      │ Service that EXPOSES tools (provides capabilities)      │
│ MCP Client      │ Service that CALLS tools (consumes capabilities)        │
│ Tool            │ A single function the AI can invoke                     │
│ Transport       │ How messages travel (HTTP, SSE, stdio)                  │
│ JSON-RPC        │ Message format used by MCP                              │
└─────────────────┴──────────────────────────────────────────────────────────┘
```

### 2.2 Server vs Client

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   MCP CLIENT                              MCP SERVER                        │
│   (Gateway)                               (Transaction Tools)               │
│                                                                             │
│   ┌───────────────┐                       ┌───────────────┐                │
│   │               │   "List tools"        │               │                │
│   │   Asks:       │ ───────────────────▶  │   Responds:   │                │
│   │   What can    │                       │   Here are    │                │
│   │   you do?     │ ◀───────────────────  │   my tools    │                │
│   │               │   [tool1, tool2...]   │               │                │
│   └───────────────┘                       └───────────────┘                │
│                                                                             │
│   ┌───────────────┐                       ┌───────────────┐                │
│   │               │   "Call tool X"       │               │                │
│   │   Requests:   │ ───────────────────▶  │   Executes:   │                │
│   │   Run this    │                       │   Runs tool,  │                │
│   │   tool        │ ◀───────────────────  │   returns     │                │
│   │               │   {result: ...}       │   result      │                │
│   └───────────────┘                       └───────────────┘                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Transport Options

```
┌─────────────────┬────────────────────────────────────────────────────────────┐
│ TRANSPORT       │ USE CASE                                                  │
├─────────────────┼────────────────────────────────────────────────────────────┤
│ SSE             │ Server-Sent Events over HTTP (web-friendly)               │
│ (Used here)     │ Client connects, server pushes messages                   │
├─────────────────┼────────────────────────────────────────────────────────────┤
│ Streamable HTTP │ Newer MCP transport, bidirectional streaming              │
├─────────────────┼────────────────────────────────────────────────────────────┤
│ stdio           │ Standard input/output (for local processes)               │
└─────────────────┴────────────────────────────────────────────────────────────┘
```

───────────────────────────────────────────────────────────────────────────────
## 3. MCP TOOLS IN THIS PROJECT
───────────────────────────────────────────────────────────────────────────────

### 3.1 Tool Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MCP SERVER: Transaction Server                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   TOOL 1: search_transactions                                               │
│   ─────────────────────────────────────────────────────────────────────     │
│   Purpose: Find transactions matching criteria                              │
│   Returns: List of transactions                                             │
│                                                                             │
│   TOOL 2: get_transaction                                                   │
│   ─────────────────────────────────────────────────────────────────────     │
│   Purpose: Get details for one transaction                                  │
│   Returns: Single transaction object                                        │
│                                                                             │
│   TOOL 3: flag_for_review                                                   │
│   ─────────────────────────────────────────────────────────────────────     │
│   Purpose: Mark transactions for human review                               │
│   Returns: Count of updated transactions                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Tool: search_transactions

```
PURPOSE: Search transactions with filters

INPUT PARAMETERS:
┌─────────────────┬──────────┬────────────────────────────────────────────────┐
│ PARAMETER       │ REQUIRED │ DESCRIPTION                                   │
├─────────────────┼──────────┼────────────────────────────────────────────────┤
│ merchant_name   │ No       │ Partial match (e.g., "Amazon")                │
│ min_amount      │ No       │ Minimum amount (e.g., 1000)                   │
│ max_amount      │ No       │ Maximum amount (e.g., 5000)                   │
│ risk_level      │ No       │ "low", "medium", or "high"                    │
│ status          │ No       │ "pending", "approved", "declined", "flagged"  │
│ country_code    │ No       │ 2-letter code (e.g., "US")                    │
│ date_from       │ No       │ Start date (YYYY-MM-DD)                       │
│ date_to         │ No       │ End date (YYYY-MM-DD)                         │
│ limit           │ No       │ Max results (default: 10, max: 100)           │
└─────────────────┴──────────┴────────────────────────────────────────────────┘

EXAMPLE CALL:
{
  "tool": "search_transactions",
  "arguments": {
    "risk_level": "high",
    "min_amount": 10000
  }
}

EXAMPLE RESPONSE:
{
  "transactions": [
    {
      "transaction_id": "TXN-001",
      "amount": 15000.00,
      "merchant_name": "Luxury Watches Inc",
      "risk_level": "high",
      "status": "pending"
    },
    ...
  ]
}
```

### 3.3 Tool: get_transaction

```
PURPOSE: Get full details for one transaction

INPUT PARAMETERS:
┌─────────────────┬──────────┬────────────────────────────────────────────────┐
│ PARAMETER       │ REQUIRED │ DESCRIPTION                                   │
├─────────────────┼──────────┼────────────────────────────────────────────────┤
│ transaction_id  │ Yes      │ Transaction ID (e.g., "TXN-001")              │
└─────────────────┴──────────┴────────────────────────────────────────────────┘

EXAMPLE CALL:
{
  "tool": "get_transaction",
  "arguments": {
    "transaction_id": "TXN-001"
  }
}

EXAMPLE RESPONSE:
{
  "transaction_id": "TXN-001",
  "amount": 15000.00,
  "currency": "USD",
  "merchant_name": "Luxury Watches Inc",
  "merchant_category": "jewelry",
  "card_last_four": "4242",
  "status": "pending",
  "risk_level": "high",
  "country_code": "US",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 3.4 Tool: flag_for_review

```
PURPOSE: Flag transactions for human review

INPUT PARAMETERS:
┌─────────────────┬──────────┬────────────────────────────────────────────────┐
│ PARAMETER       │ REQUIRED │ DESCRIPTION                                   │
├─────────────────┼──────────┼────────────────────────────────────────────────┤
│ transaction_ids │ Yes      │ Array of IDs ["TXN-001", "TXN-002"]           │
│ reason          │ Yes      │ Why flagging (e.g., "Suspicious pattern")     │
└─────────────────┴──────────┴────────────────────────────────────────────────┘

EXAMPLE CALL:
{
  "tool": "flag_for_review",
  "arguments": {
    "transaction_ids": ["TXN-001", "TXN-002"],
    "reason": "Unusual high-value purchases from new merchant"
  }
}

EXAMPLE RESPONSE:
{
  "updated_count": 2,
  "transaction_ids": ["TXN-001", "TXN-002"]
}
```

───────────────────────────────────────────────────────────────────────────────
## 4. MCP MESSAGE FLOW
───────────────────────────────────────────────────────────────────────────────

### 4.1 Tool Discovery

```
STEP 1: Client asks "What tools do you have?"
─────────────────────────────────────────────────────────────────────────────

CLIENT → SERVER:
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}

SERVER → CLIENT:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "search_transactions",
        "description": "Search transactions with filters",
        "inputSchema": { ... }
      },
      {
        "name": "get_transaction",
        "description": "Get transaction details",
        "inputSchema": { ... }
      },
      {
        "name": "flag_for_review",
        "description": "Flag transactions for review",
        "inputSchema": { ... }
      }
    ]
  }
}
```

### 4.2 Tool Execution

```
STEP 2: Client calls a tool
─────────────────────────────────────────────────────────────────────────────

CLIENT → SERVER:
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_transactions",
    "arguments": {
      "risk_level": "high"
    }
  },
  "id": 2
}

SERVER → CLIENT:
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"transaction_id\": \"TXN-001\", ...}]"
      }
    ]
  }
}
```

───────────────────────────────────────────────────────────────────────────────
## 5. MCP SERVER STRUCTURE
───────────────────────────────────────────────────────────────────────────────

### 5.1 File Organization

```
mcp-transactions/
├── Dockerfile
├── pyproject.toml
└── src/
    └── transaction_server/
        ├── __init__.py
        ├── server.py      ← MCP setup, tool registration
        ├── tools.py       ← Tool implementations
        ├── db.py          ← Database queries
        └── schemas.py     ← Data models
```

### 5.2 Key Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FILE          │ RESPONSIBILITY                                             │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ server.py     │ • Initialize FastMCP                                       │
│               │ • Register tools with @mcp.tool() decorator                │
│               │ • Configure transport (SSE)                                │
│               │ • Manage lifecycle (startup/shutdown)                      │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ tools.py      │ • Actual tool logic                                        │
│               │ • Input validation                                         │
│               │ • Call database layer                                      │
│               │ • Format responses                                         │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ db.py         │ • Database connection pool                                 │
│               │ • SQL queries                                              │
│               │ • Connection lifecycle                                     │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ schemas.py    │ • Pydantic models                                          │
│               │ • Input/output validation                                  │
└───────────────┴─────────────────────────────────────────────────────────────┘
```

### 5.3 Tool Registration Pattern

```python
# Simplified example of how tools are registered

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("transaction-server")

@mcp.tool()
async def search_transactions(
    merchant_name: str | None = None,
    risk_level: str | None = None,
    min_amount: float | None = None,
    limit: int = 10
) -> list[dict]:
    """Search transactions with optional filters."""
    
    # Tool implementation here
    results = await db.search(...)
    return results
```

───────────────────────────────────────────────────────────────────────────────
## 6. UI + MCP INTEGRATION
───────────────────────────────────────────────────────────────────────────────

### 6.1 How UI Displays MCP Activity

```
USER TYPES: "Show high-risk transactions"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MCP TOOL CALLS                                                    [Expand] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🔵 REQUEST    10:23:45                                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  User: "Show high-risk transactions"                                        │
│                                                                             │
│  🟡 REASONING  10:23:46                                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  I need to search for transactions with risk_level = HIGH                   │
│                                                                             │
│  🟢 MCP REQUEST  10:23:46                                                   │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Tool: search_transactions                                                  │
│  Args: { "risk_level": "high" }                                             │
│                                                                             │
│  🟢 MCP RESPONSE  10:23:47                                                  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Status: success | Records: 5                                               │
│  [View Full Response]                                                       │
│                                                                             │
│  ⚪ COMPLETE  10:23:47                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  "Found 5 high-risk transactions..."                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Phase Colors

```
┌─────────────────┬─────────┬──────────────────────────────────────────────────┐
│ PHASE           │ COLOR   │ MEANING                                         │
├─────────────────┼─────────┼──────────────────────────────────────────────────┤
│ REQUEST         │ 🔵 Blue  │ User's original message                         │
│ REASONING       │ 🟡 Yellow│ AI thinking about what to do                    │
│ MCP_REQUEST     │ 🟢 Green │ Tool being called                               │
│ MCP_RESPONSE    │ 🟢 Green │ Tool returned result                            │
│ GOVERNANCE      │ 🔴 Red   │ Policy check or restriction                     │
│ APPROVAL        │ 🟠 Orange│ Waiting for human approval                      │
│ COMPLETE        │ ⚪ Gray  │ Final response to user                          │
└─────────────────┴─────────┴──────────────────────────────────────────────────┘
```

### 6.3 UI Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User types message in chat                                              │
│                    │                                                        │
│                    ▼                                                        │
│  2. UI sends POST /chat/stream to Gateway                                   │
│                    │                                                        │
│                    ▼                                                        │
│  3. Gateway streams SSE events back to UI                                   │
│                    │                                                        │
│                    ▼                                                        │
│  4. UI receives events:                                                     │
│     • "thinking" → Update reasoning panel                                   │
│     • "tool_call" → Show MCP request in panel                               │
│     • "tool_result" → Show MCP response in panel                            │
│     • "response" → Update chat with final answer                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

───────────────────────────────────────────────────────────────────────────────
## 7. LEARNING PATH
───────────────────────────────────────────────────────────────────────────────

### 7.1 Recommended Order

```
┌─────┬───────────────────────────────────────────────────────────────────────┐
│ #   │ TOPIC                                                                │
├─────┼───────────────────────────────────────────────────────────────────────┤
│ 1   │ Understand JSON-RPC basics                                           │
│     │ → Request/response format, method names, IDs                         │
├─────┼───────────────────────────────────────────────────────────────────────┤
│ 2   │ Read MCP specification                                               │
│     │ → https://modelcontextprotocol.io                                    │
├─────┼───────────────────────────────────────────────────────────────────────┤
│ 3   │ Study FastMCP Python SDK                                             │
│     │ → @mcp.tool() decorator pattern                                      │
├─────┼───────────────────────────────────────────────────────────────────────┤
│ 4   │ Build a simple MCP server                                            │
│     │ → One tool, hardcoded response                                       │
├─────┼───────────────────────────────────────────────────────────────────────┤
│ 5   │ Connect MCP client to server                                         │
│     │ → List tools, call a tool                                            │
├─────┼───────────────────────────────────────────────────────────────────────┤
│ 6   │ Add database integration                                             │
│     │ → Real data from PostgreSQL                                          │
├─────┼───────────────────────────────────────────────────────────────────────┤
│ 7   │ Build UI visualization                                               │
│     │ → Display tool calls in real-time                                    │
└─────┴───────────────────────────────────────────────────────────────────────┘
```

### 7.2 Key Files to Study

```
PRIORITY ORDER:
─────────────────────────────────────────────────────────────────────────────

1. mcp-transactions/src/transaction_server/server.py
   → How MCP server is initialized and tools are registered

2. gateway/src/gateway/mcp_client.py
   → How to connect to MCP server and call tools

3. mcp-transactions/src/transaction_server/tools.py
   → How tool logic is implemented

4. ui/src/ui/app.py
   → How UI displays MCP activity
```

### 7.3 Concepts to Master

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONCEPT                │ WHY IT MATTERS                                    │
├────────────────────────┼────────────────────────────────────────────────────┤
│ Tool Schema            │ Defines what inputs a tool accepts                │
│ JSON-RPC               │ Message format for all MCP communication          │
│ SSE Transport          │ How messages flow over HTTP                       │
│ Tool Discovery         │ How clients learn what tools exist                │
│ Tool Execution         │ How clients invoke tools                          │
│ Error Handling         │ How errors are reported in MCP format             │
│ Async/Await            │ Python pattern used throughout                    │
└────────────────────────┴────────────────────────────────────────────────────┘
```

───────────────────────────────────────────────────────────────────────────────
## 8. QUICK REFERENCE
───────────────────────────────────────────────────────────────────────────────

### 8.1 MCP Python SDK Imports

```python
# Server-side
from mcp.server.fastmcp import FastMCP

# Client-side
from mcp import ClientSession
from mcp.client.sse import sse_client
```

### 8.2 Common Patterns

```python
# Create MCP server
mcp = FastMCP("server-name")

# Register a tool
@mcp.tool()
async def my_tool(param1: str, param2: int = 10) -> dict:
    """Tool description shown to AI."""
    return {"result": "..."}

# Start server with SSE transport
app = mcp.sse_app()
```

### 8.3 Debugging Tips

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROBLEM                    │ CHECK                                         │
├────────────────────────────┼─────────────────────────────────────────────────┤
│ Tools not discovered       │ Is server running? Check /health endpoint     │
│ 404 on /mcp                │ SSE vs Streamable HTTP mismatch               │
│ Tool returns empty         │ Check database connection                     │
│ UI not showing tool calls  │ SSE streaming enabled? Check event names      │
└────────────────────────────┴─────────────────────────────────────────────────┘
```
