```
 ─────────────────────────────────────────────────────────────────────────   
  CURRENT SYSTEM:                                                             
 ─────────────────────────────────────────────────────────────────────────   
 • MCP Server      → Exposes 3 tools (search, get, flag)                     
 • Gateway         → Deterministic in ENFORCEMENT (applies policies)         
 • Agent           → Autonomous in REASONING (decides what tools to call)    
 • LLM calls       → Uses OpenAI API for natural language understanding      
                     (Use LiteLLM for multi-model Support)                   
 • UI (Gradio)     → Displays tool calls and results                                                                                                     
 ─────────────────────────────────────────────────────────────────────────   

                                                     
 ─────────────────────────────────────────────────────────────────────────
 LLM PROVIDER                                                             
 ─────────────────────────────────────────────────────────────────────────    
    a) OpenAI API             ← Primary                                      
            i) gpt-4o         ← default (best reasoning)                     
           ii) gpt-4o-mini    ← cheaper, still good                          
          iii) gpt-3.5-turbo  ← cheapest                                     
                                                                             
    b) Claude API (Anthropic) ←  Secondary                                   
            a) Sonnet 4.5     ←  default                                     
            b) Opus 4.5       ←  expensive                                   
                                                                             
    c) Local model (Ollama)                                                  
 ─────────────────────────────────────────────────────────────────────────   

                                                                             
 ─────────────────────────────────────────────────────────────────────────   
 OPENAI API KEY                                                           
 ─────────────────────────────────────────────────────────────────────────   
    How should the API key be provided?                                      
     a) Environment variable  ← primary                       
     b) Config file           ←   Override                                                                                                  
 ─────────────────────────────────────────────────────────────────────────   


 ─────────────────────────────────────────────────────────────────────────                                                                                
 AGENT [AUTONOMOUS REASONING]             
 ─────────────────────────────────────────────────────────────────────────      
    ReAct Agent   
     • Understands natural language                                          
     • Decides which tools to call                                           
     • Proposes actions
     • Avoid recursive state creation issues 
     
    Reasoning pattern:                                                       
     • ReAct  → Reason + Act loop                                            
     • Explicit thinking:  Thought → Action → Observation                 
                                                    
 ─────────────────────────────────────────────────────────────────────────   
                    
                                                                             
 ─────────────────────────────────────────────────────────────────────────                                                                                
 POLICY ENGINE [DETERMINISTIC]                                            
 ─────────────────────────────────────────────────────────────────────────   
    • Deterministic rule enforcement
    • Policy integration before tool execution
        • Checks action against rules (ALLOW / DENY / REQUIRE_APPROVAL)   
        • HITL approval triggers                                    
    • Logs everything 
      - Policy check start
      - Each rule check  (Log actual values vs threshold) 
      - Final decision                                                             
                                                                             
        ALLOW          DENY            REQUIRE_APPROVAL                      
         │              │                   │                                
         ▼              ▼                   ▼                                
     Execute tool    Return error      Pause + notify UI                     
                                       (wait for human)                      
                                                                             
    STARTER POLICIES:                                                        
    ──────────────────────────────────────────────────────────────────────   
    ┌───────────────────────┬─────────────────┬────────────────────────┐       
    │ RULE                  │ TRIGGER         │ ACTION                 │       
    ├───────────────────────┼─────────────────┼────────────────────────┤       
    │ bulk_flag             │ flag > 5 txns   │ REQUIRE_APPROVAL       │       
    │ high_risk_flag        │ reason contains │ REQUIRE_APPROVAL       │       
    │                       │ "fraud","high"  │                        │     
    │ sensitive_merchant    │ "casino","adult"│ REQUIRE_APPROVAL       │       
    │ high_value_search     │ amount > 50000  │ ALLOW (logged)         │       
    │ rate_limit            │ > 10 calls      │ DENY                   │       
    │ sensitive_merchant    │ "casino","adult"│ REQUIRE_APPROVAL       │       
    └───────────────────────┴─────────────────┴────────────────────────┘       
 ─────────────────────────────────────────────────────────────────────────   
                
                
                                                                             
 ─────────────────────────────────────────────────────────────────────────                                                                                
 HITL (HUMAN-IN-THE-LOOP) APPROVAL                                        
 ─────────────────────────────────────────────────────────────────────────   
    UI supported approval workflows                                           
      • show "Approve/Reject" buttons when policy requires   
      • Close approval section after approve/reject                

 ─────────────────────────────────────────────────────────────────────────   
  
  
                                                                             
 ─────────────────────────────────────────────────────────────────────────   
 CONFIGURABLE VARIABLES                                                   
 ─────────────────────────────────────────────────────────────────────────   
                                                                            
 ┌─────────────────────┬─────────────────┬───────────────────────────────┐  
 │ VARIABLE            │ DEFAULT         │ DESCRIPTION                   │  
 ├─────────────────────┼─────────────────┼───────────────────────────────┤  
 │ OPENAI_API_KEY      │ (required)      │ Your OpenAI API key           │  
 │ OPENAI_MODEL        │ gpt-4o          │ Model for agent reasoning     │  
 │ POSTGRES_USER       │ mcp_user        │ Database username             │  
 │ POSTGRES_PASSWORD   │ mcp_password    │ Database password             │  
 │ POSTGRES_DB         │ transactions_db │ Database name                 │  
 │ MCP_PORT            │ 8001            │ MCP server port               │  
 │ GATEWAY_PORT        │ 8002            │ Gateway port                  │  
 │ UI_PORT             │ 7860            │ Gradio UI port                │  
 │ LOG_LEVEL           │ INFO            │ Logging verbosity             │  
 └─────────────────────┴─────────────────┴───────────────────────────────┘  
                                                                            
 ─────────────────────────────────────────────────────────────────────────   


 ─────────────────────────────────────────────────────────────────────────   
 UI             
 ─────────────────────────────────────────────────────────────────────────  
  → "🤖 Agent Chat" tab
      - HITL approval panel accordion below chat
        Add hint about triggering HITL approval
      - MCP Message Flow accordion below HITL
      - ReAct steps panel 
      
  
  → "🤖 Search Transactions" tab
  
  
  
  → "🤖 Get Transactions" tab
  
  
  
  → "📋 Policy" tab
  
  
  
  → "📜 Audit" tab
  
 ─────────────────────────────────────────────────────────────────────────   
 CODE EXECUTION FLOW (To be displayed in UI)
 ───────────────────────────────────────────────────────────────────────── 

┌──────────────────────────────────────────────────────────────────────────────┐
│ KEY FEATURES OF DESIGN                                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ 1. HIERARCHICAL NESTING                                                      │
│    ─────────────────────────────────────────────────────────────────────     │
│    • Each component is a child of its caller                                 │
│    • Visually shows request depth                                            │
│    • Collapse/expand to focus on specific parts                              │
│                                                                              │
│ 2. INPUT → PROCESSING → OUTPUT at EVERY NODE                                 │
│    ─────────────────────────────────────────────────────────────────────     │
│    • Every node shows what it received (INPUT)                               │
│    • What it did (PROCESSING/REASONING)                                      │
│    • What it returned (OUTPUT)                                               │
│                                                                              │
│ 3. CLEAR COMPONENT OWNERSHIP                                                 │
│    ─────────────────────────────────────────────────────────────────────     │
│    • Icons + labels identify WHO is acting                                   │
│    • Agent = 🤖 (REASONING - autonomous)                                     │
│    • Gateway = ⚖️ (ENFORCEMENT - deterministic)                              │
│    • MCP = 🔧 (EXECUTION - tool logic)                                       │
│                                                                              │
│ 4. PROTOCOL VISIBILITY                                                       │
│    ─────────────────────────────────────────────────────────────────────     │
│    • Shows actual JSON-RPC messages                                          │
│    • Shows SSE event format                                                  │
│    • Shows HTTP endpoints                                                    │
│                                                                              │
│ 5. TIMING INFORMATION                                                        │
│    ─────────────────────────────────────────────────────────────────────     │
│    • Timestamp on each node                                                  │
│    • Can calculate latency between steps                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ EXAMPLE: WHAT IT COULD LOOK LIKE                                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ CONCEPT: Each request becomes a tree with expandable nodes                   │
│          Click any node to see INPUT → PROCESSING → OUTPUT                   │
│                                                                              │
│ VISUAL EXAMPLE:                                                              │
│ ──────────────────────────────────────────────────────────────────────────── │
│                                                                              │
│ ▼ 🔵 USER REQUEST                                          10:23:45          │
│       📍 Location:  gateway/main.py:98                                       │
│       ⚡  Function:  call_tool(request)                                       │
│       🕐 Time:      2026-03-08T22:15:30                                      │
│       ⏱️ Duration:  45 ms                                                    │
│ │   "Show high-risk transactions over $10,000"                               │
│ │                                                                            │
│ ├─▼ 📤 UI → GATEWAY                                        10:23:45          │
│ │      📍 Location:  gateway/main.py:98                                      │   
│ │      ⚡  Function:  call_tool(request)                                      │   
│ │      🕐 Time:      2026-03-08T22:15:30                                     │   
│ │      ⏱️ Duration:  45 ms                                                   │   
│ │ │   ┌─ INPUT ──────────────────────────────────────────┐                   │
│ │ │   │ POST /chat/stream                                │                   │
│ │ │   │ { "message": "Show high-risk transactions..." }  │                   │
│ │ │   └──────────────────────────────────────────────────┘                   │
│ │ │                                                                          │
│ │ ├─▼ 🤖 GATEWAY → AGENT (LLM)                             10:23:45          │
│ │ │ │    📍 Location:  gateway/main.py:98                                    │
│ │ │ │    ⚡  Function:  call_tool(request)                                    │
│ │ │ │    🕐 Time:      2026-03-08T22:15:30                                   │
│ │ │ │    ⏱️ Duration:  45 ms                                                 │
│ │ │ │   ┌─ INPUT ──────────────────────────────────────────┐                 │
│ │ │ │   │ System: You are a transaction search agent...    │                 │
│ │ │ │   │ User: "Show high-risk transactions..."           │                 │
│ │ │ │   │ Tools: [search_transactions, get_transaction...] │                 │
│ │ │ │   └──────────────────────────────────────────────────┘                 │
│ │ │ │   ┌─ OUTPUT (REASONING) ─────────────────────────────┐                 │
│ │ │ │   │ THOUGHT: User wants high-risk transactions       │                 │
│ │ │ │   │          with amount > $10,000                   │                 │
│ │ │ │   │ ACTION: Call search_transactions tool            │                 │
│ │ │ │   │ ARGS: { risk_level: "high", min_amount: 10000 }  │                 │
│ │ │ │   └──────────────────────────────────────────────────┘                 │
│ │ │ │                                                                        │
│ │ │ ├─▶ ⚖️ GATEWAY: POLICY CHECK                           10:23:46          │
│ │ │ │      📍 Location:  gateway/main.py:98                                  │ 
│ │ │ │      ⚡  Function:  call_tool(request)                                  │
│ │ │ │      🕐 Time:      2026-03-08T22:15:30                                 │ 
│ │ │ │      ⏱️ Duration:  45 ms                                               │
│ │ │ │     ┌─ INPUT ──────────────────────────────────────┐                   │
│ │ │ │     │ Tool: search_transactions                    │                   │
│ │ │ │     │ Args: { risk_level: "high", min_amount:...}  │                   │
│ │ │ │     └──────────────────────────────────────────────┘                   │
│ │ │ │     ┌─ RULE EVALUATION ────────────────────────────┐                   │
│ │ │ │     │ ✅ Tool allowed: search_transactions         │                   │
│ │ │ │     │ ✅ No sensitive fields requested             │                   │
│ │ │ │     │ ✅ No approval required for search           │                   │
│ │ │ │     └──────────────────────────────────────────────┘                   │
│ │ │ │     ┌─ OUTPUT ─────────────────────────────────────┐                   │
│ │ │ │     │ DECISION: ALLOW                              │                   │
│ │ │ │     └──────────────────────────────────────────────┘                   │
│ │ │ │                                                                        │
│ │ │ ├─▼ 🔧 GATEWAY → MCP SERVER                            10:23:46          │
│ │ │ │      📍 Location:  gateway/main.py:98                                  │ 
│ │ │ │      ⚡  Function:  call_tool(request)                                  │
│ │ │ │      🕐 Time:      2026-03-08T22:15:30                                 │ 
│ │ │ │      ⏱️ Duration:  45 ms                                               │
│ │ │ │ │   ┌─ MCP REQUEST (JSON-RPC) ─────────────────────┐                   │
│ │ │ │ │   │ {                                            │                   │
│ │ │ │ │   │   "jsonrpc": "2.0",                          │                   │
│ │ │ │ │   │   "method": "tools/call",                    │                   │
│ │ │ │ │   │   "params": {                                │                   │
│ │ │ │ │   │     "name": "search_transactions",           │                   │
│ │ │ │ │   │     "arguments": {                           │                   │
│ │ │ │ │   │       "risk_level": "high",                  │                   │
│ │ │ │ │   │       "min_amount": 10000                    │                   │
│ │ │ │ │   │     }                                        │                   │
│ │ │ │ │   │   },                                         │                   │
│ │ │ │ │   │   "id": 2                                    │                   │
│ │ │ │ │   │ }                                            │                   │
│ │ │ │ │   └──────────────────────────────────────────────┘                   │
│ │ │ │ │                                                                      │
│ │ │ │ ├─▶ 🗄️ MCP SERVER: TOOL EXECUTION                   10:23:46           │
│ │ │ │ │      📍 Location:  gateway/main.py:98                                │ 
│ │ │ │ │      ⚡  Function:  call_tool(request)                                │
│ │ │ │ │      🕐 Time:      2026-03-08T22:15:30                               │ 
│ │ │ │ │      ⏱️ Duration:  45 ms                                             │
│ │ │ │ │     ┌─ PROCESSING ───────────────────────────────┐                   │
│ │ │ │ │     │ 1. Validate input schema                   │                   │
│ │ │ │ │     │ 2. Build SQL query                         │                   │
│ │ │ │ │     │ 3. Execute: SELECT * FROM transactions     │                   │
│ │ │ │ │     │    WHERE risk_level='high'                 │                   │
│ │ │ │ │     │    AND amount >= 10000                     │                   │
│ │ │ │ │     │ 4. Format results                          │                   │
│ │ │ │ │     └──────────────────────────────────────────────┘                 │
│ │ │ │ │                                                                      │
│ │ │ │ └─◀ 📦 MCP RESPONSE                                  10:23:47          │
│ │ │ │        📍 Location:  gateway/main.py:98                                │ 
│ │ │ │        ⚡  Function:  call_tool(request)                                │
│ │ │ │        🕐 Time:      2026-03-08T22:15:30                               │ 
│ │ │ │        ⏱️ Duration:  45 ms                                             │
│ │ │ │       ┌─ MCP RESPONSE (JSON-RPC) ──────────────────┐                   │
│ │ │ │       │ {                                          │                   │
│ │ │ │       │   "jsonrpc": "2.0",                        │                   │
│ │ │ │       │   "id": 2,                                 │                   │
│ │ │ │       │   "result": {                              │                   │
│ │ │ │       │     "content": [{                          │                   │
│ │ │ │       │       "type": "text",                      │                   │
│ │ │ │       │       "text": "[{\"transaction_id\":...}]" │                   │
│ │ │ │       │     }]                                     │                   │
│ │ │ │       │   }                                        │                   │
│ │ │ │       │ }                                          │                   │
│ │ │ │       └──────────────────────────────────────────────┘                 │
│ │ │ │                                                                        │
│ │ │ └─◀ 🤖 AGENT: OBSERVATION                              10:23:47          │
│ │ │        📍 Location:  gateway/main.py:98                                  │ 
│ │ │        ⚡  Function:  call_tool(request)                                  │
│ │ │        🕐 Time:      2026-03-08T22:15:30                                 │ 
│ │ │        ⏱️ Duration:  45 ms                                               │
│ │ │       ┌─ OBSERVATION ────────────────────────────────┐                   │
│ │ │       │ Tool returned 3 transactions:                │                   │
│ │ │       │ • TXN-001: $15,000 (Luxury Watches)          │                   │
│ │ │       │ • TXN-007: $12,500 (Electronics)             │                   │
│ │ │       │ • TXN-012: $18,000 (Jewelry)                 │                   │
│ │ │       └──────────────────────────────────────────────┘                   │
│ │ │       ┌─ NEXT THOUGHT ───────────────────────────────┐                   │
│ │ │       │ I have the results. No more tools needed.    │                   │
│ │ │       │ ACTION: Return final answer to user.         │                   │
│ │ │       └──────────────────────────────────────────────┘                   │
│ │ │                                                                          │
│ │ └─◀ 📤 GATEWAY → UI (SSE Stream)                         10:23:47          │
│ │         📍 Location:  gateway/main.py:98                                   │ 
│ │         ⚡  Function:  call_tool(request)                                   │
│ │         🕐 Time:      2026-03-08T22:15:30                                  │ 
│ │         ⏱️ Duration:  45 ms                                                │
│ │       ┌─ SSE EVENTS ───────────────────────────────────┐                   │
│ │       │ event: thinking                                │                   │
│ │       │ data: {"content": "Searching..."}              │                   │
│ │       │                                                │                   │
│ │       │ event: tool_call                               │                   │
│ │       │ data: {"tool": "search_transactions"...}       │                   │
│ │       │                                                │                   │
│ │       │ event: response                                │                   │
│ │       │ data: {"content": "Found 3 transactions..."}   │                   │
│ │       └──────────────────────────────────────────────────┘                 │
│ │                                                                            │
│ └─◀ 💬 FINAL RESPONSE TO USER                              10:23:47          │
│        📍 Location:  gateway/main.py:98                                      │ 
│        ⚡  Function:  call_tool(request)                                      │
│        🕐 Time:      2026-03-08T22:15:30                                     │ 
│        ⏱️ Duration:  45 ms                                                   │
│       ┌──────────────────────────────────────────────────┐                   │
│       │ Found 3 high-risk transactions over $10,000:     │                   │
│       │                                                  │                   │
│       │ 1. TXN-001 - $15,000 - Luxury Watches Inc        │                   │
│       │ 2. TXN-007 - $12,500 - ElectroMart               │                   │
│       │ 3. TXN-012 - $18,000 - Diamond Gallery           │                   │
│       └──────────────────────────────────────────────────┘                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TREE NODE LEGEND                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ICON   │ COMPONENT              │ RESPONSIBILITY                            │
│ ───────┼────────────────────────┼────────────────────────────────────────── │
│ 🔵     │ User Request           │ Original natural language query           │
│ 📤     │ UI → Gateway           │ HTTP POST to /chat/stream                 │
│ 🤖     │ Gateway → Agent        │ LLM call with tools + reasoning           │
│ ⚖️     │ Gateway Policy         │ Deterministic rule enforcement            │
│ 🔧     │ Gateway → MCP          │ JSON-RPC tool call                        │
│ 🗄️     │ MCP Tool Execution     │ Database query + processing               │
│ 📦     │ MCP Response           │ JSON-RPC result                           │
│ 💬     │ Final Response         │ Natural language answer                   │
│                                                                             │
│ ARROWS:                                                                     │
│ ───────┼──────────────────────────────────────────────────────────────────  │
│ ▼      │ Expand (click to see details)                                      │
│ ▶      │ Collapsed (click to expand)                                        │
│ ─▶     │ Outgoing request (right arrow)                                     │
│ ─◀     │ Incoming response (left arrow)                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

TREE VIEW:
□ Shows system prompt in GATEWAY → AGENT node
□ Hierarchical: USER → UI→GATEWAY → GATEWAY→AGENT → 
                THOUGHT/ACTION → MCP REQUEST → MCP RESPONSE → FINAL
                
□ ReAct badges: 🧠 THOUGHT (yellow), ⚡ ACTION (green), 
                👁️ OBSERVATION (blue), ✅ FINAL ANSWER (purple)












































       
 ─────────────────────────────────────────────────────────────────────────   


 
 ─────────────────────────────────────────────────────────────────────────   
 AUDIT LOGS             
 ─────────────────────────────────────────────────────────────────────────    
    Policy steps 
      - Policy check start
      - Each rule check  (Log actual values vs threshold) 
      - Final decision     



 ─────────────────────────────────────────────────────────────────────────   
 DEPENDENCIES            
 ─────────────────────────────────────────────────────────────────────────  
┌────────────────────────────────────┬──────────────────────────────────────┐
│ LIBRARY                            │  DESCRIPTION                         │
├────────────────────────────────────┼──────────────────────────────────────┤
│  # Async Support                   │                                      │
│  "aiohttp>=3.13.3",                │  Async HTTP Framework                │  
│  "anyio>=4.12.1",                  │  networking & concurrency library    │   
│  "asyncpg>=0.31.0",                │  PostgreSQL DB interface library     │   
│                                    │                                      │
│  # MCP                             │                                      │ 
│  "fastmcp>=3.0.0",                 │ Server authoring (resources + tools) │ 
│  "mcp[cli]>=1.25.0",               │ MCP CLI                              │ 
│                                    │                                      │
│  # Web Framework                   │                                      │   
│  "fastapi>=0.135.1",               │  Web Framework                       │   
│  "uvicorn>=0.41.0",                │  ASGI web server                     │ 
│  "httpx>=0.28.1",                  │  HTTP client library                 │
│                                    │                                      │   
│                                    │                                      │
│  # OpenAI (Agent LLM)              │                                      │
│  "openai>=2.0.0,<3",               │  Agent LLM                           │
│                                    │                                      │
│  # Data Validation                 │                                      │
│  "pydantic>=2.10.4,<2.12",         │                                      │
│  "pydantic-settings>=2.1.0",       │  Settings management                 │
│                                    │                                      │
│                                    │                                      │
│  # Logging                         │                                      │
│  "structlog>=24.1.0",              │  Structured logging                  │
│  "python-json-logger>=4.0.0",      │                                      │
│                                    │                                      │
│  # Environment variables           │                                      │
│  "python-dotenv>=1.0.1",           │  Environment variables               │
│                                    │                                      │   
└────────────────────────────────────┴──────────────────────────────────────┘

```

