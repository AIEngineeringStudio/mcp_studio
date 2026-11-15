# MCP Learning Documentation

## Complete Guide with Code References

═══════════════════════════════════════════════════════════════════════════════

## 1. MCP OVERVIEW

### 1.1 What is MCP?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MCP = Model Context Protocol                                               │
│                                                                             │
│  DEFINITION:                                                                │
│  A standardized protocol that allows AI models/agents to discover           │
│  and access external tools in a consistent way.                             │
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
• No standard discovery               • Built-in tool discovery 
```

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
│  ├── JSON-RPC 2.0 ─────────── Communication protocol (Message format)       │
│  └── Transport ────────────── How messages travel                           │
│       ├── SSE (Server-Sent Events)                                          │
│       ├── Streamable HTTP                                                   │
│       └── stdio                                                             │
│                                                                             │
│  COMPONENT LAYER                                                            │
│  ├── MCP Server ───────────── Exposes capabilities                          │
│  └── MCP Client ───────────── Consumes capabilities                         │
│                                                                             │
│  CAPABILITY LAYER                                                           │
│  ├── Tools ────────────────── Executable functions AI can call              │
│  ├── Resources ────────────── Data AI can read                              │
│  ├── Prompts ──────────────── Prompt Templates AI can use                   │
│  └── Sampling ─────────────── AI can request LLM calls                      │
│                                                                             │
│  LIFECYCLE LAYER                                                            │
│  ├── Initialization ───────── Capability negotiation                        │
│  ├── Discovery ────────────── List available items                          │
│  ├── Invocation ───────────── Call tools / read resources                   │
│  └── Shutdown ─────────────── Clean disconnect                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 MCP High-Level Architecture

```


                     ┌──────────────────────────┐
                     │        MCP CLIENT        │
                     │  (AI IDE / Agent / App)  │
                     └────────────┬─────────────┘
                                  │ JSON-RPC Messages
                                  ▼
                     ┌──────────────────────────┐
                     │        TRANSPORT         │
                     ├──────────────────────────┤
                     │     stdio                │
                     │     SSE                  │
                     │     Streamable HTTP      │
                     └────────────┬─────────────┘
                                  │ JSON-RPC Messages
                                  ▼
                     ┌──────────────────────────┐
                     │        MCP SERVER        │
                     │ (tools + data + prompts) │
                     └────────────┬─────────────┘
                                  │                             
          ┌───────────────────────┼─────────────────────────┐
          │                       │                         │
          ▼                       ▼                         ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐ 
│         TOOLS        │ │      RESOURCES       │ │       PROMPTS        │ 
│       (actions)      │ │        (data)        │ │     (templates)      │ 
├──────────────────────┤ ├──────────────────────┤ ├──────────────────────┤ 
│   tools/list         │ │  resources/list      │ │   prompts/list       │ 
│   tools/call         │ │  resources/read      │ │   prompts/get        │ 
│   streaming          │ │  subscriptions       │ │   arguments          │
│   progress           │ │  templates           │ │   sampling           │ 
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘   
```


### 2.3 Tool Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   MCP CLIENT                              MCP SERVER                        │
│                                                                             │
│   ┌───────────────┐                       ┌───────────────┐                 │
│   │               │   "tools/list"        │               │                 │
│   │   Asks:       │ ───────────────────▶  │   Responds:   │                 │
│   │   What can    │                       │   Here are    │                 │
│   │   you do?     │ ◀───────────────────  │   my tools    │                 │
│   │               │   [tool1, tool2...]   │               │                 │
│   └───────────────┘                       └───────────────┘                 │
│                                                                             │
│   ┌───────────────┐                       ┌───────────────┐                 │
│   │               │    "tools/list"       │               │                 │
│   │   Requests:   │ ───────────────────▶  │   Executes:   │                 │
│   │   Run this    │                       │   Runs tool,  │                 │
│   │   tool        │ ◀───────────────────  │   returns     │                 │
│   │               │   {result: ...}       │   result      │                 │
│   └───────────────┘                       └───────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tool Definition Structure
```
{
 "name": "get_weather",
 "description": "Get weather for a city",
 "inputSchema": {
   "type": "object",
   "properties": {
      "city": {
         "type": "string"
      }
   }
 }
}
```

### Tool Operations

```
 ┌─────────────────────┬───────────────────────────────┐  
 │ CATEGORY            │ MEANINIG                      │  
 ├─────────────────────┼───────────────────────────────┤  
 │ tool/list           │ discover available tools      │  
 │ tool/call           │ execute tool                  │  
 │ streaming           │ partial outputs               │  
 │ progress updates    │ execution status              │  
 │ cancel              │ stop tool                     │  
 └─────────────────────┴───────────────────────────────┘  
```

### 2.4 Term Definitions

```
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ TERM             │ DEFINITION                                              │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Server       │ A service that EXPOSES tools/resources/prompts.         │
│                  │ It waits for requests and executes them.                │
│                  │ MEMORIZE: "Server = Provider = Exposes"                 │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Client       │ A service that CALLS tools/resources/prompts.           │
│                  │ It discovers and calls what servers expose.             │
│                  │ MEMORIZE: "Client = Consumer = Calls"                   │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Tool             │ A function that AI can invoke to perform an action.     │
│                  │ Has: name, description, input schema, output.           │
│                  │ Example: search_transactions, send_email                │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Resource         │ Read-only data exposed by server.                       │
│                  │ Has: URI, name, mime type, contents.                    │
│                  │ Example: file://config.json, db://users                 │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Prompt           │ A reusable template for AI interactions.                │
│                  │ Has: name, description, arguments, messages.            │
│                  │ Example: "summarize_document" prompt template           │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Transport        │ The communication channel between client/server.        │
│                  │ How messages travel                                     │
│                  │ Options: SSE, Streamable HTTP, stdio                    │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ JSON-RPC 2.0     │ The message format used by MCP.                         │
│                  │ Every message has: jsonrpc, method/result, id           │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Capability       │ A feature that server/client supports.                  │
│                  │ Negotiated during initialization.                       │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Session          │ A connection between client and server.                 │
│                  │ Maintains state during communication.                   │
└──────────────────┴─────────────────────────────────────────────────────────┘
```

### 2.4 Transport Options Explained

```
┌─────────────────┬──────────────────────────────────────────────────────────┐
│ TRANSPORT       │ DETAILS                                                  │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ SSE             │ Server-Sent Events over HTTP                             │
│                 │                                                          │
│                 │  Use SSE when:                                           │
│                 │  - responses are long running &                          │
│                 │  - updates must be streamed                              │
│                 │  - over a single connection                              │
│                 │  - without the client repeatedly polling.                │
│                 │                                                          │
│                 │ HOW IT WORKS:                                            │
│                 │ • Client opens HTTP connection to /sse endpoint          │
│                 │ • Server pushes events down the connection               │
│                 │ • Client sends requests via separate POST                │
│                 │                                                          │
│                 │ PROS: Web-friendly, firewall-friendly                    │
│                 │ CONS: Unidirectional (server → client for events)        │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ Streamable HTTP │ Newer bidirectional HTTP streaming                       │
│                 │                                                          │
│                 │ HOW IT WORKS:                                            │
│                 │ • Single HTTP connection for both directions             │
│                 │ • Uses chunked transfer encoding                         │
│                 │                                                          │
│                 │ PROS: Simpler, truly bidirectional                       │
│                 │ CONS: Newer, less tooling support                        │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ stdio           │ Standard input/output pipes                              │
│                 │                                                          │
│                 │ HOW IT WORKS:                                            │
│                 │ • Client spawns server as subprocess                     │
│                 │ • Communication via stdin/stdout                         │
│                 │                                                          │
│                 │ PROS: Simple for local tools                             │
│                 │ CONS: Only works locally                                 │
└─────────────────┴──────────────────────────────────────────────────────────┘
```

## MCP Concepts Breakdown

### 1. Core Architecture

These are the **foundation concepts**.

| Category | Feature                                 | Description                                                             | 
|----------|-----------------------------------------|-------------------------------------------------------------------------| 
| ✓ Core   | MCP Server                              | Program exposing tools/resources/prompts                                | 
| ✓ Core   | MCP Client                              | App connecting to server <br/>(AI IDE, agent, assistant)                | 
| ✓ Core   | MCP Protocol Messaging <br/>(JSON-RPC ) | Communication protocol used by MCP                                      | 
| ✓ Core   | Initialize Handshake                    | Client/server capability negotiation <br/>(Declares supported features) | 
| ✓ Core   | Protocol Compatibility                  | Protocol version compatibility                                          | 
| ✓ Core   | Connection lifecycle                    | Initialize → Ready → Running → Close                                    | 
| IC       | Session Management                      | Client session tracking                                                 | 

#### MCP CONNECTION LIFECYCLE

```
Client                     Server
  │                          │
  │ connect                  │
  ├─────────────────────────►│
  │ initialize               │
  ├─────────────────────────►│
  │                          │
  │      capabilities        │
  │◄─────────────────────────┤
  │                          │
  │ initialized              │
  ├─────────────────────────►│
  │                          │
  │      READY STATE         │
```

### 2. Tool System (Primary MCP Feature)

Tools are the **main reason MCP exists**.

| Category   | Feature                           | Description                           |
|------------|-----------------------------------|---------------------------------------|
| ✓ Core     | Tool Registration                 | Server exposes tool                   |
| ✓ Core     | Tool Discovery `(tools/list)`     | Client queries available tools        |
| ✓ Core     | Tool  Execution `(tools/call)`    | Client invokes tool                   |
| ✓ Core     | Input Schema (validate arguments) | JSON schema describing tool arguments |
| ~ Advanced | Tool Streaming                    | Stream partial tool output            |
| ~ Advanced | Execution progress                | Tool execution Updates/Notifications  |
| ~ Advanced | Cancel tool execution             | Stop long running tool                |

**Tool Architecture:**

```
 Client
   │ tools/list
   ▼
 Server ────► returns tool definitions


 Client
   │ tools/call
   ▼
 Server ────► executes tool
    │ 
    ▼
 Response
```


### 3. Resource System (Second Major Feature)

Resources expose **data instead of actions**.

| Category   | Feature              | Description                                |
|------------|----------------------|--------------------------------------------|
| ✓ Core     | Resources            | Data accessible by URI                     |
| ~ Advanced | Templates            | Parameterized resource URIs                |
| ~ Advanced | Subscriptions        | Subscribe to resource update notifications |
| ~ Advanced | BlobResourceContents | Binary resource content support            |
| ~ Advanced | Pagination           | Partial listing of resources               |
| ~ Advanced | Roots                | Resource namespace roots                   |

**Flow:**

```
Client
   |
   | resources/list
   v
Server returns resources

Client
   |
   | resources/read
   v
Server returns content
```

Resources use URIs.

**Examples:**

```
file://docs/api.md
db://users/123
logs://server/errors
```

### 4. Prompt System

Prompts are **templates for AI input**.

**Purpose:**

- standardize prompts
- parameterized prompts
- reuse prompt logic

| Category   | Feature          | Description                          |
|------------|------------------|--------------------------------------|
| ✓ Core     | Prompts          | Prompt templates hosted on server    |
| ✓ Core     | Prompt Arguments | Dynamic prompt parameters            |
| ~ Advanced | Sampling         | Server can requests model generation |

**Flow:**

```
Client
   |
   | prompts/list
   v
Server returns prompts

Client
   |
   | prompts/get
   v
Server returns prompt template
```

**Prompt Template Example**

```
Prompt: summarize_document

Template:
"Summarize the following document:

{{document}}

Focus on:
- key insights
- decisions
- risks"
```

Arguments:

```
{
 "document": "text here"
}
```

### 5. Transport Layer

How MCP messages travel. Transport carries JSON-RPC messages.

| Category  | Feature                   | Description                  |
|-----------|---------------------------|------------------------------|
| Transport | stdio Transport           | Local process transport      |
| Transport | SSE Transport             | Server-sent events over HTTP |
| Transport | Streamable HTTP Transport | HTTP streaming of responses  |

| Transport      | Use Case            |
|----------------|---------------------|
| stdio          | Local process tools |
| SSE            | Web streaming       |
| HTTP streaming | Remote MCP servers  |

```
 Client
  │
  │ JSON-RPC
  ▼
 Transport
  │
  ▼
 Server
```

### 6. Notifications and Messaging

MCP supports two JSON-RPC message types.

| Category   | Feature                    | Description               | 
|------------|----------------------------|---------------------------| 
| ✓ Core     | Message type: Request      | Requires response         | 
| ✓ Core     | Message type: Notification | Fire-and-forget           | 
| ~ Advanced | Logging to Client          | Server logs forwarded     |  
| IC         | Debug/Message logging      | Debugging message traffic | 

```
Request:         → response expected
    {
      "method": "tools/list"
    }

    Response:
    {
      "tools": [...]
    }


Notification:   → no response
    progress/update   
    log/message 
    resource/changed
```

### 7. Runtime & Operational Features

These are **operational features**, not core protocol.

| Category | Feature        | Description                         |
|----------|----------------|-------------------------------------|
| IC       | Authentication | Access control                      |
| IC       | Rate Limiting  | Server throttling to prevent abuse  |
| IC       | Health Checks  | Server status monitoring            |
| IC       | Error Handling | Structured JSON-RPC error responses |

### 8. AI / Agent Integration

| Category   | Feature                 | Description               | 
|------------|-------------------------|---------------------------| 
| ~ Advanced | AI Agent Integration    | Agent orchestrated tools  | 
| ~ Advanced | Human-in-the-Loop(HITL) | User approval workflow    | 
| ~ Advanced | Elicitation             | Server asks user for info | 

**Elicitation:**

```
Tool requires confirmation

Server
  │
  │ elicitation request
  ▼
Client
  │
  │ ask user
  ▼
User response
```

### 9. Data & Content Features

| Category   | Feature                | Description              |
|------------|------------------------|--------------------------|
| ✓ Core     | Multiple Content Types | Rich response formats    |
| ~ Advanced | Embedding Support      | Return vector embeddings |

| Content Type | Example     |
|--------------|-------------|
| text         | markdown    |
| image        | PNG         |
| blob         | binary file |
| embeddings   | vectors     |

### 10. Implementation Patterns

Important for Python/Node MCP servers.

| Category | Feature             | Description                   |
|----------|---------------------|-------------------------------|
| IC       | Async/Await Pattern | Non-blocking server execution |

**Legend**

* ✓ Core = Core MCP concept
* ~ Advanced = Advanced capability
* IC = Implementation concern (not protocol feature)

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
│   │   (Frontend)    │  • Displays forms for each tool                       │
│   └────────┬────────┘  • Shows MCP message flow                             │
│            │                                                                │
│            │ HTTP POST /tools/call                                          │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │    GATEWAY      │  Port 8002                                            │
│   │  (MCP Client)   │  • Connects to MCP Server                             │
│   └────────┬────────┘  • Logs all messages                                  │
│            │                                                                │
│            │ SSE Transport (JSON-RPC)                                       │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │   MCP SERVER    │  Port 8001                                            │
│   │ (Tool Provider) │  • Exposes 3 tools                                    │
│   └────────┬────────┘  • Executes tool logic                                │
│            │                                                                │
│            │ SQL Queries                                                    │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │   POSTGRESQL    │  Port 5432                                            │
│   │   (Database)    │  • Stores 50 transactions                             │
│   └─────────────────┘                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

```
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ COMPONENT        │ RESPONSIBILITIES                                        │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Gradio UI        │ • Accept user input (filters, IDs, etc.)                │
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

## 7. MESSAGE FLOW DEEP DIVE

### 7.1 JSON-RPC Message Format Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 REQUEST                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",        // Always "2.0"                                │
│     "method": "tools/call",  // The method being called                     │
│     "params": {...},         // Method parameters                           │
│     "id": 1                  // Request ID (for matching response)          │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 SUCCESS RESPONSE                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",        // Always "2.0"                                │
│     "id": 1,                 // Matches request ID                          │
│     "result": {...}          // The result data                             │
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
│       "code": -32600,        // Error code                                  │
│       "message": "Invalid Request",                                         │
│       "data": {...}          // Optional additional info                    │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Complete Message Flow Example

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
│       "clientInfo": {"name": "gateway", "version": "1.0.0"}                 │
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
│       "serverInfo": {"name": "transaction-server", "version": "1.0.0"}      │
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
│   2. Looks up "search_transactions" in registry                             │
│   3. Calls tools.search_transactions(risk_level="high", limit=10)           │
│   4. tools.py calls db.search_transactions(...)                             │
│   5. db.py executes SQL query against PostgreSQL                            │
│   6. Results flow back up: db → tools → server                              │
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
│           "text": "{\"transactions\":[{\"transaction_id\":\"TX-001\",...}]}"│
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
│     "arguments": {"risk_level": "high", "limit": 10},                       │
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
│ initialize          │ Start session, negotiate capabilities                 │
│ tools/list          │ Get list of available tools                           │
│ tools/call          │ Execute a tool                                        │
│ resources/list      │ Get list of available resources                       │
│ resources/read      │ Read a resource's content                             │
│ prompts/list        │ Get list of available prompts                         │
│ prompts/get         │ Get a prompt template                                 │
│ notifications/*     │ Various notification types                            │
│ ping                │ Keep connection alive                                 │
└─────────────────────┴───────────────────────────────────────────────────────┘
```

### 8.4 Debugging Checklist

```
┌─────────────────────────────┬───────────────────────────────────────────────┐
│ PROBLEM                     │ CHECK                                         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Tools not discovered        │ Is MCP server running? Check /health          │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ 404 on /sse                 │ SSE vs Streamable HTTP mismatch               │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Tool returns empty          │ Check database connection                     │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Connection refused          │ Check port, network, Docker networking        │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ JSON parse error            │ Tool not returning valid JSON string          │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Timeout                     │ Long-running tool, increase timeout           │
└─────────────────────────────┴───────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════

## SUMMARY: KEY TAKEAWAYS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MEMORIZE THESE                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ 1. MCP = Standard protocol for AI to call tools                             │
│                                                                             │
│ 2. Server EXPOSES tools, Client CALLS tools                                 │
│                                                                             │
│ 3. All messages use JSON-RPC 2.0 format                                     │
│                                                                             │
│ 4. Tools are registered with @mcp.tool() decorator                          │
│                                                                             │
│ 5. Tool discovery: tools/list                                               │
│    Tool execution: tools/call                                               │
│                                                                             │
│ 6. SSE transport is web-friendly (used in this example)                     │
│                                                                             │
│ 7. Tools return JSON strings, not Python objects                            │
│                                                                             │
│ 8. Session.initialize() must be called before any other method              │
│                                                                             │
│ 9. NOT IMPLEMENTED: Resources, Prompts, Sampling, Progress, Streaming       │
│                                                                             │
│ 10. Study order: server.py → mcp_client.py → tools.py → db.py → app.py      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════
