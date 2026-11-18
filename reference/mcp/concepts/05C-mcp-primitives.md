## MCP Primitives

Core MCP concept such as tool/resource/prompt

### Tools System

Tool is an executable operation.
Use a tool when something must be **performed**.

Tools are the **main reason MCP exists**.

**Tool Operations**

| Category   | Feature                           | Description                           |
|------------|-----------------------------------|---------------------------------------|
| ✓ Core     | Registration                      | Server exposes tool                   |
| ✓ Core     | Discovery `(tools/list)`          | Client queries available tools        |
| ✓ Core     | Execution `(tools/call)`          | Client invokes tool                   |
| ✓ Core     | Input Schema (validate arguments) | JSON schema describing tool arguments |
| ~ Advanced | Streaming                         | Stream partial tool output            |
| ~ Advanced | Execution progress                | Tool execution Updates/Notifications  |
| ~ Advanced | Cancel execution                  | Stop long running tool                |

**Tool Architecture**

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

### 3. Resource System (Second Major Feature)

Resources expose **data instead of actions**.
Use a resource when something must be **retrieved or inspected**.

| Category   | Feature              | Description                                |
|------------|----------------------|--------------------------------------------|
| ✓ Core     | Resources            | Readable context accessible by an URI      |
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
config://application
customer://123/profile
schema://orders
```

### 4. Prompt System

Prompt is a **reusable interaction template**.

Use a prompt when the server wants to provide a recommended workflow or
structured instruction to the host.

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
