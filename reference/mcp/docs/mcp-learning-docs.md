# MCP Learning Documentation
## Complete Guide with Code References

═══════════════════════════════════════════════════════════════════════════════

## TABLE OF CONTENTS

1. [MCP Overview](#1-mcp-overview)
2. [Core Concepts](#2-core-concepts)
3. [Architecture Patterns](#3-architecture-patterns)
4. [Code Walkthrough](#4-code-walkthrough)
5. [Concepts Implemented](#5-concepts-implemented)
6. [Concepts NOT Implemented](#6-concepts-not-implemented)
7. [Message Flow Deep Dive](#7-message-flow-deep-dive)
8. [Quick Reference](#8-quick-reference)

═══════════════════════════════════════════════════════════════════════════════

## 1. MCP OVERVIEW

### 1.1 What is MCP?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MCP = Model Context Protocol                                               │
│                                                                             │
│  DEFINITION:                                                                │
│  A standardized protocol that allows AI models/agents to discover          │
│  and invoke external tools in a consistent way.                            │
│                                                                             │
│  ANALOGY:                                                                   │
│  Like USB for devices — any tool that speaks MCP can plug into             │
│  any AI system that supports MCP.                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Why MCP Exists

| Problem Without MCP          | Solution With MCP              |
|------------------------------|--------------------------------|
| Custom integration per tool  | Standard interface for all     |
| Tight coupling               | Loose coupling                 |
| Hard to swap/add tools       | Easy plug-and-play             |
| Vendor lock-in               | Interoperability               |
| No standard discovery        | Built-in tool discovery        |

### 1.3 MCP Specification Source

Official specification: https://modelcontextprotocol.io

═══════════════════════════════════════════════════════════════════════════════

## 2. CORE CONCEPTS

### 2.1 Concept Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MCP CONCEPT HIERARCHY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROTOCOL LAYER                                                             │
│  ├── JSON-RPC 2.0 ─────────── Message format                               │
│  └── Transport ────────────── How messages travel                          │
│       ├── SSE (Server-Sent Events)                                         │
│       ├── Streamable HTTP                                                   │
│       └── stdio                                                             │
│                                                                             │
│  COMPONENT LAYER                                                            │
│  ├── MCP Server ───────────── Exposes capabilities                         │
│  └── MCP Client ───────────── Consumes capabilities                        │
│                                                                             │
│  CAPABILITY LAYER                                                           │
│  ├── Tools ────────────────── Functions AI can call                        │
│  ├── Resources ────────────── Data AI can read                             │
│  ├── Prompts ──────────────── Templates AI can use                         │
│  └── Sampling ─────────────── AI can request LLM calls                     │
│                                                                             │
│  LIFECYCLE LAYER                                                            │
│  ├── Initialization ───────── Capability negotiation                       │
│  ├── Discovery ────────────── List available items                         │
│  ├── Invocation ───────────── Call tools / read resources                  │
│  └── Shutdown ─────────────── Clean disconnect                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Term Definitions

```
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ TERM             │ DEFINITION                                              │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Server       │ A service that EXPOSES tools/resources/prompts.        │
│                  │ It waits for requests and executes them.               │
│                  │ MEMORIZE: "Server = Provider = Exposes"                │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Client       │ A service that CONSUMES tools/resources/prompts.       │
│                  │ It discovers and calls what servers expose.            │
│                  │ MEMORIZE: "Client = Consumer = Calls"                  │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Tool             │ A function that performs an action.                    │
│                  │ Has: name, description, input schema, output.          │
│                  │ Example: search_transactions, send_email               │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Resource         │ Read-only data exposed by server.                      │
│                  │ Has: URI, name, mime type, contents.                   │
│                  │ Example: file://config.json, db://users                │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Prompt           │ A reusable template for AI interactions.               │
│                  │ Has: name, description, arguments, messages.           │
│                  │ Example: "summarize_document" prompt template          │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Transport        │ The communication channel between client/server.       │
│                  │ Options: SSE, Streamable HTTP, stdio                   │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ JSON-RPC 2.0     │ The message format used by MCP.                        │
│                  │ Every message has: jsonrpc, method/result, id          │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Capability       │ A feature that server/client supports.                 │
│                  │ Negotiated during initialization.                      │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Session          │ A connection between client and server.                │
│                  │ Maintains state during communication.                  │
└──────────────────┴─────────────────────────────────────────────────────────┘
```

### 2.3 Transport Options Explained

```
┌─────────────────┬──────────────────────────────────────────────────────────┐
│ TRANSPORT       │ DETAILS                                                  │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ SSE             │ Server-Sent Events over HTTP                            │
│ (Used in this   │                                                          │
│  example)       │ HOW IT WORKS:                                            │
│                 │ • Client opens HTTP connection to /sse endpoint         │
│                 │ • Server pushes events down the connection              │
│                 │ • Client sends requests via separate POST               │
│                 │                                                          │
│                 │ PROS: Web-friendly, firewall-friendly                   │
│                 │ CONS: Unidirectional (server → client for events)       │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ Streamable HTTP │ Newer bidirectional HTTP streaming                      │
│ (Not used)      │                                                          │
│                 │ HOW IT WORKS:                                            │
│                 │ • Single HTTP connection for both directions            │
│                 │ • Uses chunked transfer encoding                        │
│                 │                                                          │
│                 │ PROS: Simpler, truly bidirectional                      │
│                 │ CONS: Newer, less tooling support                       │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ stdio           │ Standard input/output pipes                             │
│ (Not used)      │                                                          │
│                 │ HOW IT WORKS:                                            │
│                 │ • Client spawns server as subprocess                    │
│                 │ • Communication via stdin/stdout                        │
│                 │                                                          │
│                 │ PROS: Simple for local tools                            │
│                 │ CONS: Only works locally                                │
└─────────────────┴──────────────────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════

## 3. ARCHITECTURE PATTERNS

### 3.1 This Project's Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   USER                                                                      │
│     │                                                                       │
│     ▼                                                                       │
│   ┌─────────────────┐                                                       │
│   │   GRADIO UI     │  Port 7860                                            │
│   │   (Frontend)    │  • Displays forms for each tool                      │
│   └────────┬────────┘  • Shows MCP message flow                            │
│            │                                                                │
│            │ HTTP POST /tools/call                                          │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │    GATEWAY      │  Port 8002                                            │
│   │  (MCP Client)   │  • Connects to MCP Server                            │
│   └────────┬────────┘  • Logs all messages                                 │
│            │                                                                │
│            │ SSE Transport (JSON-RPC)                                       │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │   MCP SERVER    │  Port 8001                                            │
│   │ (Tool Provider) │  • Exposes 3 tools                                   │
│   └────────┬────────┘  • Executes tool logic                               │
│            │                                                                │
│            │ SQL Queries                                                    │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │   POSTGRESQL    │  Port 5432                                            │
│   │   (Database)    │  • Stores 50 transactions                            │
│   └─────────────────┘                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

```
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ COMPONENT        │ RESPONSIBILITIES                                        │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Gradio UI        │ • Accept user input (filters, IDs, etc.)               │
│ (ui/app.py)      │ • Call Gateway API                                      │
│                  │ • Display results                                       │
│                  │ • Visualize MCP message flow                            │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Gateway          │ • Act as MCP Client                                     │
│ (gateway/)       │ • Maintain MCP session                                  │
│                  │ • Log all JSON-RPC messages                             │
│                  │ • Expose REST API for UI                                │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Server       │ • Register tools with @mcp.tool()                       │
│ (mcp-server/)    │ • Handle tools/list requests                            │
│                  │ • Handle tools/call requests                            │
│                  │ • Execute tool logic                                    │
│                  │ • Query database                                        │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ PostgreSQL       │ • Store transaction data                                │
│ (db/)            │ • Execute queries                                       │
│                  │ • Return results                                        │
└──────────────────┴─────────────────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════

## 4. CODE WALKTHROUGH

### 4.1 MCP Server Code Analysis

#### FILE: mcp-server/src/transaction_server/server.py

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: Creating MCP Server Instance
# ─────────────────────────────────────────────────────────────────────────────

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="transaction-server",   # Server identifier
    version="1.0.0"              # Server version
)

# WHAT THIS DOES:
# • Creates an MCP server object
# • Prepares tool registry
# • Sets up JSON-RPC handler
```

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: Tool Registration with Decorator
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_transactions(
    merchant_name: Optional[str] = None,   # Optional parameter
    risk_level: Optional[str] = None,      # Optional parameter
    limit: int = 10                         # Default value
) -> str:
    """Search transactions with optional filters."""  # Tool description
    return await tools.search_transactions(...)

# WHAT THIS DOES:
# • @mcp.tool() registers function as MCP tool
# • Function signature becomes input schema
# • Docstring becomes tool description
# • Return type is always string (JSON)

# THE DECORATOR CREATES THIS SCHEMA AUTOMATICALLY:
# {
#   "name": "search_transactions",
#   "description": "Search transactions with optional filters.",
#   "inputSchema": {
#     "type": "object",
#     "properties": {
#       "merchant_name": {"type": "string"},
#       "risk_level": {"type": "string"},
#       "limit": {"type": "integer", "default": 10}
#     }
#   }
# }
```

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: SSE Transport Setup
# ─────────────────────────────────────────────────────────────────────────────

# Get SSE application from MCP
mcp_app = mcp.sse_app()

# Mount on FastAPI
app.mount("/", mcp_app)

# WHAT THIS DOES:
# • Creates /sse endpoint for SSE connections
# • Creates /messages endpoint for client requests
# • Handles JSON-RPC message routing
```

#### FILE: mcp-server/src/transaction_server/tools.py

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: Tool Implementation
# ─────────────────────────────────────────────────────────────────────────────

async def search_transactions(
    merchant_name: Optional[str] = None,
    min_amount: Optional[float] = None,
    # ... more parameters
) -> str:
    """
    Search transactions with optional filters.
    
    IMPORTANT: Tools return JSON strings, not Python objects.
    The MCP protocol expects text content.
    """
    # 1. Validate inputs (optional, Pydantic can do this)
    limit = max(1, min(100, limit))
    
    # 2. Execute business logic (database query)
    transactions = await db.search_transactions(...)
    
    # 3. Build response object
    result = {
        "transactions": transactions,
        "total_count": len(transactions),
        "filters_applied": filters_applied
    }
    
    # 4. Return as JSON string
    return json.dumps(result)

# KEY POINTS:
# • Tools are async functions
# • Tools return JSON strings
# • Tools should handle their own errors
# • Tools can call any external service (DB, API, etc.)
```

#### FILE: mcp-server/src/transaction_server/db.py

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: Database Layer (Separate from MCP)
# ─────────────────────────────────────────────────────────────────────────────

# Connection pool management
_pool: Optional[asyncpg.Pool] = None

async def init_pool() -> asyncpg.Pool:
    """Initialize database connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, ...)
    return _pool

# Query function
async def search_transactions(...) -> list[dict]:
    """Execute search query."""
    async with get_connection() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

# KEY POINTS:
# • Database logic is separate from MCP logic
# • Uses connection pooling for efficiency
# • Returns Python objects (tools.py converts to JSON)
```

### 4.2 MCP Client Code Analysis

#### FILE: gateway/src/gateway/mcp_client.py

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: MCP Client Connection
# ─────────────────────────────────────────────────────────────────────────────

from mcp import ClientSession
from mcp.client.sse import sse_client

async def list_tools(self) -> list[dict]:
    """Discover available tools."""
    
    # 1. Open SSE connection to server
    async with sse_client(self.server_url) as (read, write):
        
        # 2. Create client session
        async with ClientSession(read, write) as session:
            
            # 3. Initialize session (capability negotiation)
            await session.initialize()
            
            # 4. Request tool list
            tools_result = await session.list_tools()
            
            return tools_result.tools

# WHAT HAPPENS DURING INITIALIZATION:
# • Client sends: {"jsonrpc":"2.0","method":"initialize",...}
# • Server responds with capabilities
# • Both sides know what features are supported
```

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: Tool Invocation
# ─────────────────────────────────────────────────────────────────────────────

async def call_tool(self, tool_name: str, arguments: dict) -> dict:
    """Call a tool on the MCP server."""
    
    async with sse_client(self.server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Call the tool
            tool_result = await session.call_tool(
                tool_name,          # e.g., "search_transactions"
                arguments=arguments  # e.g., {"risk_level": "high"}
            )
            
            # Parse response
            # tool_result.content is a list of content blocks
            # Usually contains TextContent with JSON string
            
            return parsed_result

# JSON-RPC MESSAGE SENT:
# {
#   "jsonrpc": "2.0",
#   "method": "tools/call",
#   "params": {
#     "name": "search_transactions",
#     "arguments": {"risk_level": "high"}
#   },
#   "id": 1
# }

# JSON-RPC RESPONSE RECEIVED:
# {
#   "jsonrpc": "2.0",
#   "id": 1,
#   "result": {
#     "content": [
#       {"type": "text", "text": "{\"transactions\":[...]}"}
#     ]
#   }
# }
```

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: Message Logging for Visualization
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MCPLogEntry:
    """Log entry for MCP message."""
    timestamp: str
    phase: str      # REQUEST, MCP_REQUEST, MCP_RESPONSE, COMPLETE, ERROR
    direction: str  # CLIENT_TO_SERVER, SERVER_TO_CLIENT
    method: Optional[str] = None
    tool_name: Optional[str] = None
    content: Optional[Any] = None
    duration_ms: Optional[int] = None

def _log(self, phase: str, direction: str, ...):
    """Add entry to message log."""
    entry = MCPLogEntry(
        timestamp=datetime.utcnow().isoformat(),
        phase=phase,
        direction=direction,
        ...
    )
    self.log.append(entry)

# THIS ENABLES:
# • UI to show exactly what messages are sent/received
# • Understanding of MCP protocol in action
# • Debugging of tool calls
```

### 4.3 UI Code Analysis

#### FILE: ui/src/ui/app.py

```python
# ─────────────────────────────────────────────────────────────────────────────
# CONCEPT: Visualizing MCP Message Flow
# ─────────────────────────────────────────────────────────────────────────────

PHASE_STYLES = {
    "REQUEST":      {"emoji": "🔵", "color": "#3b82f6"},
    "DISCOVERY":    {"emoji": "🟣", "color": "#8b5cf6"},
    "MCP_REQUEST":  {"emoji": "🟢", "color": "#22c55e"},
    "MCP_RESPONSE": {"emoji": "🟢", "color": "#22c55e"},
    "COMPLETE":     {"emoji": "⚪", "color": "#6b7280"},
    "ERROR":        {"emoji": "🔴", "color": "#ef4444"},
}

def format_message_log(log: list[dict]) -> str:
    """Format log entries for display."""
    # Shows each message with:
    # • Phase emoji and label
    # • Timestamp
    # • Direction arrow
    # • Tool name
    # • Duration
    # • Full JSON content
```

═══════════════════════════════════════════════════════════════════════════════

## 5. CONCEPTS IMPLEMENTED

### 5.1 Implementation Status Table

```
┌─────────────────────────────┬────────────┬─────────────────────────────────┐
│ CONCEPT                     │ STATUS     │ WHERE IN CODE                   │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ MCP Server                  │ ✅ YES     │ mcp-server/server.py            │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ MCP Client                  │ ✅ YES     │ gateway/mcp_client.py           │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Tool Registration           │ ✅ YES     │ server.py: @mcp.tool()          │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Tool Discovery (tools/list) │ ✅ YES     │ mcp_client.py: list_tools()     │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Tool Execution (tools/call) │ ✅ YES     │ mcp_client.py: call_tool()      │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ SSE Transport               │ ✅ YES     │ server.py: mcp.sse_app()        │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ JSON-RPC Messages           │ ✅ YES     │ Handled by MCP SDK              │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Input Schema (auto-gen)     │ ✅ YES     │ Function signatures → schema    │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Async/Await Pattern         │ ✅ YES     │ All functions are async         │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Session Management          │ ✅ YES     │ ClientSession context manager   │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Connection Lifecycle        │ ✅ YES     │ FastAPI lifespan, pool mgmt     │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Health Checks               │ ✅ YES     │ /health endpoints               │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Error Handling              │ ✅ YES     │ Try/catch in client, tools      │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Message Logging             │ ✅ YES     │ MCPLogEntry in mcp_client.py    │
└─────────────────────────────┴────────────┴─────────────────────────────────┘
```

### 5.2 Implemented Tools Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TOOL 1: search_transactions                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ PURPOSE:  Find transactions matching criteria                               │
│ INPUTS:   merchant_name, min_amount, max_amount, risk_level,               │
│           status, country_code, date_from, date_to, limit                  │
│ OUTPUT:   List of transactions + metadata                                   │
│ FILES:    server.py (registration), tools.py (logic), db.py (query)        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TOOL 2: get_transaction                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ PURPOSE:  Get full details for one transaction                              │
│ INPUTS:   transaction_id (required)                                         │
│ OUTPUT:   Complete transaction record                                       │
│ FILES:    server.py (registration), tools.py (logic), db.py (query)        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TOOL 3: flag_for_review                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ PURPOSE:  Mark transactions for human review                                │
│ INPUTS:   transaction_ids (list), reason (required)                        │
│ OUTPUT:   Update count + flagged IDs                                        │
│ FILES:    server.py (registration), tools.py (logic), db.py (update)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════

## 6. CONCEPTS NOT IMPLEMENTED

### 6.1 Not Implemented Table

```
┌─────────────────────────────┬────────────┬─────────────────────────────────┐
│ CONCEPT                     │ STATUS     │ DESCRIPTION                     │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Resources                   │ ❌ NO      │ Read-only data exposed by       │
│                             │            │ server (files, configs, etc.)   │
│                             │            │                                 │
│                             │            │ HOW TO ADD:                     │
│                             │            │ @mcp.resource("file://{path}")  │
│                             │            │ async def read_file(path): ...  │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Prompts                     │ ❌ NO      │ Reusable templates for AI       │
│                             │            │ interactions.                   │
│                             │            │                                 │
│                             │            │ HOW TO ADD:                     │
│                             │            │ @mcp.prompt()                   │
│                             │            │ async def analyze_txn(): ...    │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Sampling                    │ ❌ NO      │ Server requesting LLM calls     │
│                             │            │ from client.                    │
│                             │            │                                 │
│                             │            │ USE CASE:                       │
│                             │            │ Tool needs AI to process data   │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Streamable HTTP Transport   │ ❌ NO      │ Newer bidirectional transport.  │
│                             │            │ We use SSE instead.             │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ stdio Transport             │ ❌ NO      │ For local subprocess tools.     │
│                             │            │ We use network (SSE).           │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Capability Negotiation      │ ⚠️ PARTIAL │ Happens in SDK, not visible     │
│                             │            │ in our code.                    │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Progress Notifications      │ ❌ NO      │ Server sending progress during  │
│                             │            │ long-running tools.             │
│                             │            │                                 │
│                             │            │ HOW TO ADD:                     │
│                             │            │ await ctx.report_progress(...)  │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Logging to Client           │ ❌ NO      │ Server sending log messages     │
│                             │            │ to client for debugging.        │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Cancellation                │ ❌ NO      │ Client cancelling in-progress   │
│                             │            │ tool calls.                     │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Roots                       │ ❌ NO      │ Client exposing filesystem      │
│                             │            │ roots to server.                │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Authentication              │ ❌ NO      │ No auth between components.     │
│                             │            │ Add via API keys or OAuth.      │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ AI Agent Integration        │ ❌ NO      │ No actual AI/LLM calling tools. │
│                             │            │ UI directly calls Gateway.      │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Tool Streaming              │ ❌ NO      │ Tools returning streamed data.  │
│                             │            │ Current tools return once.      │
├─────────────────────────────┼────────────┼─────────────────────────────────┤
│ Multiple Content Types      │ ❌ NO      │ Tools return text only.         │
│                             │            │ Could return images, etc.       │
└─────────────────────────────┴────────────┴─────────────────────────────────┘
```

### 6.2 How to Add Missing Concepts

#### Adding Resources

```python
# In server.py - Add resource exposure

@mcp.resource("config://transaction-rules")
async def get_transaction_rules() -> str:
    """Get current transaction processing rules."""
    rules = {
        "high_risk_threshold": 10000,
        "blocked_countries": ["XX", "YY"],
        "max_daily_transactions": 50
    }
    return json.dumps(rules)

# Client would call:
# resources = await session.list_resources()
# content = await session.read_resource("config://transaction-rules")
```

#### Adding Prompts

```python
# In server.py - Add prompt templates

@mcp.prompt()
async def analyze_transaction(transaction_id: str) -> list[dict]:
    """Prompt template for analyzing a transaction."""
    txn = await db.get_transaction(transaction_id)
    return [
        {
            "role": "user",
            "content": f"Analyze this transaction for fraud:\n{json.dumps(txn)}"
        }
    ]

# Client would call:
# prompts = await session.list_prompts()
# messages = await session.get_prompt("analyze_transaction", {"transaction_id": "TXN-001"})
```

#### Adding Progress Notifications

```python
# In tools.py - Report progress during long operations

async def bulk_analyze_transactions(
    transaction_ids: list[str],
    ctx: Context  # MCP provides context
) -> str:
    """Analyze multiple transactions with progress."""
    results = []
    total = len(transaction_ids)
    
    for i, txn_id in enumerate(transaction_ids):
        # Report progress
        await ctx.report_progress(
            progress=i,
            total=total,
            message=f"Analyzing {txn_id}..."
        )
        
        # Do work
        result = await analyze_one(txn_id)
        results.append(result)
    
    return json.dumps(results)
```

═══════════════════════════════════════════════════════════════════════════════

## 7. MESSAGE FLOW DEEP DIVE

### 7.1 Complete Message Flow Example

```
USER ACTION: Click "Search Transactions" with risk_level="high"

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: UI → Gateway (HTTP)                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   POST http://gateway:8002/tools/call                                       │
│   Content-Type: application/json                                            │
│                                                                             │
│   {                                                                         │
│     "tool_name": "search_transactions",                                     │
│     "arguments": {                                                          │
│       "risk_level": "high",                                                 │
│       "limit": 10                                                           │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Gateway opens SSE connection to MCP Server                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   GET http://mcp-server:8001/sse                                            │
│   Accept: text/event-stream                                                 │
│                                                                             │
│   (Connection established, ready for events)                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Gateway sends initialize (JSON-RPC)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   → CLIENT TO SERVER:                                                       │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "method": "initialize",                                                 │
│     "params": {                                                             │
│       "protocolVersion": "2024-11-05",                                      │
│       "capabilities": {},                                                   │
│       "clientInfo": {"name": "gateway", "version": "1.0.0"}                │
│     },                                                                      │
│     "id": 0                                                                 │
│   }                                                                         │
│                                                                             │
│   ← SERVER TO CLIENT:                                                       │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "id": 0,                                                                │
│     "result": {                                                             │
│       "protocolVersion": "2024-11-05",                                      │
│       "capabilities": {"tools": {}},                                        │
│       "serverInfo": {"name": "transaction-server", "version": "1.0.0"}     │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Gateway sends tools/call (JSON-RPC)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   → CLIENT TO SERVER:                                                       │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "method": "tools/call",                                                 │
│     "params": {                                                             │
│       "name": "search_transactions",                                        │
│       "arguments": {                                                        │
│         "risk_level": "high",                                               │
│         "limit": 10                                                         │
│       }                                                                     │
│     },                                                                      │
│     "id": 1                                                                 │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: MCP Server executes tool                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. server.py receives tools/call                                          │
│   2. Looks up "search_transactions" in registry                            │
│   3. Calls tools.search_transactions(risk_level="high", limit=10)          │
│   4. tools.py calls db.search_transactions(...)                            │
│   5. db.py executes SQL query against PostgreSQL                           │
│   6. Results flow back up: db → tools → server                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 6: MCP Server sends response (JSON-RPC)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ← SERVER TO CLIENT:                                                       │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "id": 1,                                                                │
│     "result": {                                                             │
│       "content": [                                                          │
│         {                                                                   │
│           "type": "text",                                                   │
│           "text": "{\"transactions\":[{\"transaction_id\":\"TXN-001\",...}]}"│
│         }                                                                   │
│       ]                                                                     │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 7: Gateway returns response to UI (HTTP)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   HTTP 200 OK                                                               │
│   Content-Type: application/json                                            │
│                                                                             │
│   {                                                                         │
│     "tool_name": "search_transactions",                                     │
│     "arguments": {"risk_level": "high", "limit": 10},                      │
│     "result": {                                                             │
│       "transactions": [...],                                                │
│       "total_count": 10                                                     │
│     },                                                                      │
│     "duration_ms": 45,                                                      │
│     "success": true,                                                        │
│     "message_log": [                                                        │
│       {"phase": "REQUEST", ...},                                            │
│       {"phase": "MCP_REQUEST", ...},                                        │
│       {"phase": "MCP_RESPONSE", ...},                                       │
│       {"phase": "COMPLETE", ...}                                            │
│     ]                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 8: UI displays results                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Left panel: Transaction results (JSON)                                    │
│   Right panel: MCP message flow (formatted log)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 JSON-RPC Message Format Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 REQUEST                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",        // Always "2.0"                               │
│     "method": "tools/call",  // The method being called                    │
│     "params": {...},         // Method parameters                          │
│     "id": 1                  // Request ID (for matching response)         │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 SUCCESS RESPONSE                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",        // Always "2.0"                               │
│     "id": 1,                 // Matches request ID                         │
│     "result": {...}          // The result data                            │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 ERROR RESPONSE                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "id": 1,                                                                │
│     "error": {                                                              │
│       "code": -32600,        // Error code                                 │
│       "message": "Invalid Request",                                        │
│       "data": {...}          // Optional additional info                   │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════

## 8. QUICK REFERENCE

### 8.1 Key Imports

```python
# SERVER SIDE
from mcp.server.fastmcp import FastMCP

# CLIENT SIDE
from mcp import ClientSession
from mcp.client.sse import sse_client
```

### 8.2 Common Patterns

```python
# CREATE SERVER
mcp = FastMCP("my-server")

# REGISTER TOOL
@mcp.tool()
async def my_tool(param: str) -> str:
    """Description shown to AI."""
    return json.dumps({"result": "..."})

# CONNECT CLIENT
async with sse_client(url) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("my_tool", {"param": "value"})
```

### 8.3 MCP Methods Reference

```
┌─────────────────────┬───────────────────────────────────────────────────────┐
│ METHOD              │ PURPOSE                                               │
├─────────────────────┼───────────────────────────────────────────────────────┤
│ initialize          │ Start session, negotiate capabilities                │
│ tools/list          │ Get list of available tools                          │
│ tools/call          │ Execute a tool                                        │
│ resources/list      │ Get list of available resources                      │
│ resources/read      │ Read a resource's content                            │
│ prompts/list        │ Get list of available prompts                        │
│ prompts/get         │ Get a prompt template                                │
│ notifications/*     │ Various notification types                           │
│ ping                │ Keep connection alive                                │
└─────────────────────┴───────────────────────────────────────────────────────┘
```

### 8.4 Debugging Checklist

```
┌─────────────────────────────┬───────────────────────────────────────────────┐
│ PROBLEM                     │ CHECK                                         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Tools not discovered        │ Is MCP server running? Check /health         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ 404 on /sse                 │ SSE vs Streamable HTTP mismatch              │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Tool returns empty          │ Check database connection                    │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Connection refused          │ Check port, network, Docker networking       │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ JSON parse error            │ Tool not returning valid JSON string         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Timeout                     │ Long-running tool, increase timeout          │
└─────────────────────────────┴───────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════

## SUMMARY: KEY TAKEAWAYS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MEMORIZE THESE                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ 1. MCP = Standard protocol for AI to call tools                            │
│                                                                             │
│ 2. Server EXPOSES tools, Client CALLS tools                                │
│                                                                             │
│ 3. All messages use JSON-RPC 2.0 format                                    │
│                                                                             │
│ 4. Tools are registered with @mcp.tool() decorator                         │
│                                                                             │
│ 5. Tool discovery: tools/list                                              │
│    Tool execution: tools/call                                              │
│                                                                             │
│ 6. SSE transport is web-friendly (used in this example)                    │
│                                                                             │
│ 7. Tools return JSON strings, not Python objects                           │
│                                                                             │
│ 8. Session.initialize() must be called before any other method             │
│                                                                             │
│ 9. NOT IMPLEMENTED: Resources, Prompts, Sampling, Progress, Streaming      │
│                                                                             │
│ 10. Study order: server.py → mcp_client.py → tools.py → db.py → app.py    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════
