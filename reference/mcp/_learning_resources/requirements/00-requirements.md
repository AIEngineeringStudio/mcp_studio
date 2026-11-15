Need you to help me build a fully functioning Transaction Search Agent
along with UI.

════════════════════════════════════════════════════════════════════════════════  
✅ ENTERPRISE PRODUCTION-GRADE ARCHITECTURE/IMPLEMENTATION  
════════════════════════════════════════════════════════════════════════════════
```
────────────────────────────────────────────────────────────────────────────────
COMPONENT              │ TECHNOLOGY                            
───────────────────────┼────────────────────────────────────────────────────────
MCP Server             │ Official MCP SDK (Python), FastAPI compatible 
                       │ - Exposes tools over MCP Streamable HTTP
                       │ - Also supports SSE streaming events
───────────────────────┼────────────────────────────────────────────────────────
API Layer              │ FastAPI (Python)                      
───────────────────────┼────────────────────────────────────────────────────────
MCP Gateway            │ FastAPI (Policy enforcement, routing, audit)  
                       │ Rate limiting (Redis) 
                       │ HITL management
                       │ Audit logging
───────────────────────┼────────────────────────────────────────────────────────
Policy Engine          │ OPA (Open Policy Agent) + for RBAC, custom for HITL 
                       │ Roles: Analyst, Manager, Compliance, Admin
                       │ Risk level restrictions: Transactions > $10,000
                       │ Audit requirements
                       │                                                                     
───────────────────────┼────────────────────────────────────────────────────────
Transaction Service    │ FastAPI + PostgreSQL       
───────────────────────┼────────────────────────────────────────────────────────
Audit Service          │ Structured logging, immutable store   
───────────────────────┼────────────────────────────────────────────────────────
Frontend               │ Gradio      
───────────────────────┼────────────────────────────────────────────────────────
Database               │ PostgreSQL (production-grade)   
───────────────────────┼────────────────────────────────────────────────────────
AUTHENTICATION         │ JWT tokens (stateless) 
───────────────────────┼────────────────────────────────────────────────────────
DEPLOYMENT TARGET      │ Docker Compose (all services) 
───────────────────────┼────────────────────────────────────────────────────────
SDK CHOICE             │ OpenAI SDK (GPT-4 via openai SDK) 
                       │  + LiteLLM (Multi-LLM)
───────────────────────┼────────────────────────────────────────────────────────
AGENT BEHAVIOR         │ ReAct Agent Loop (Think → Act → Observe cycle)
                       │ Multi-turn conversations
                       │ WebSocket streaming
                       │ HYBRID (Constrained Autonomy)
                       │  - Agent is autonomous in REASONING      
                       │  - Gateway is deterministic in ENFORCEMENT
                       │  - Policy engine decides what's allowed  
                       │ • LLM-driven with policy constraints              
                       │ • Agent proposes actions, gateway enforces rules  
                       │ • HITL for sensitive operations                                         
───────────────────────┼────────────────────────────────────────────────────────
 Package Manager       │ uv        
───────────────────────┴────────────────────────────────────────────────────────                
```
════════════════════════════════════════════════════════════════════════════════
ARCHITECTURE DIAGRAM
════════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Gradio)                              │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ HTTP/SSE
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MCP GATEWAY (FastAPI)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Auth/JWT    │  │ Rate Limit  │  │ Policy Check│  │ Audit Logger        │ │
│  └─────────────┘  └─────────────┘  └──────┬──────┘  └─────────────────────┘ │
└───────────────────────────────────────────┼─────────────────────────────────┘
                                            │
                     ┌──────────────────────┼───────────────────────┐
                     ▼                      ▼                       ▼
         ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
         │ MCP SERVER        │   │ MCP SERVER        │   │ MCP SERVER        │
         │ (Transactions)    │   │ (Risk Scoring)    │   │ (Notifications)   │
         │ Python MCP SDK    │   │ Python MCP SDK    │   │ Python MCP SDK    │
         └─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘
                   │                       │                       │
                   ▼                       ▼                       ▼
         ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
         │ Transaction API   │   │ Risk API          │   │ Notification API  │
         │ (FastAPI)         │   │ (FastAPI)         │   │ (FastAPI)         │
         └─────────┬─────────┘   └───────────────────┘   └───────────────────┘
                   │
                   ▼
         ┌───────────────────┐
         │ PostgreSQL        │
         │ (Transactions DB) │
         └───────────────────┘
```

════════════════════════════════════════════════════════════════════════════════
REQUEST FLOW: ReAct LOOP (Reasoning + Acting)
════════════════════════════════════════════════════════════════════════════════

```
  ┌─────────────────────────────────────────────────────────────────────┐    
  │                         USER QUERY                                  │    
  │        "Show high-risk transactions over $10k,                      │    
  │         then flag any that are pending for review"                  │    
  └─────────────────────────────────┬───────────────────────────────────┘   
                                    │                                        
                                    ▼ 
  ┌─────────────────────────────────────────────────────────────────────┐
  │                        ReAct AGENT                                  │                                      │
  │  STEP 1: THINK (Reasoning)                                          │    
  │  I need to: 1) search transactions with filters                     │    
  │             2) filter for risk=HIGH, transaction amount > $10,000   │    
  │             3) flag those for review                                │
  │  2. ACT:   Call search_transactions tool                            │
  └─────────────────────────────────┬───────────────────────────────────┘ 
                                    │                                        
                                    ▼                                        
  ┌─────────────────────────────────────────────────────────────────────┐ 
  │                        MCP GATEWAY                                  │ 
  │  1. Authenticate (JWT)                                              │ 
  │  2. Rate limit check (Redis)                                        │ 
  │  3. Policy check (OPA) ──────────────────────────────┐              │ 
  │     └─ Role: Manager                                 │              │ 
  │     └─ Tool: search_transactions ✓                   │              │ 
  │     └─ Risk: HIGH → REQUIRES_APPROVAL ←──────────────┘              │ 
  │  4. Return HITL request                                             │ 
  └─────────────────────────────────┬───────────────────────────────────┘ 
                                    │                                     
                                    ▼                                     
  ┌─────────────────────────────────────────────────────────────────────┐    
  │  STEP 1: THINK (Reasoning)                                          │    
  │  "I need to: 1) search transactions with filters                    │    
  │              2) filter for pending status                           │    
  │              3) flag those for review"                              │    
  └─────────────────────────────────┬───────────────────────────────────┘    
                                    │                                        
                                    ▼                                        
  ┌─────────────────────────────────────────────────────────────────────┐    
  │  STEP 2: ACT (Tool Call #1)                                         │    
  │  Tool: search_transactions                                          │    
  │  Args: { merchant: "Acme", min_amount: 10000, risk: "HIGH" }        │    
  └─────────────────────────────────┬───────────────────────────────────┘    
                                    │                                        
                       ┌────────────┴────────────┐                           
                       ▼                         ▼                           
             ┌─────────────────┐       ┌─────────────────┐                   
             │ POLICY CHECK    │       │ MCP SERVER      │                   
             │ (Gateway)       │──OK──▶│ (Execute Tool)  │                   
             └─────────────────┘       └────────┬────────┘                   
                                                │                            
                                    ▼───────────┘                            
  ┌─────────────────────────────────────────────────────────────────────┐    
  │  STEP 3: OBSERVE (Tool Result)                                      │    
  │  "Found 3 transactions: TXN-001 ($12k, APPROVED),                   │    
  │   TXN-002 ($15k, PENDING), TXN-003 ($11k, PENDING)"                 │    
  └─────────────────────────────────┬───────────────────────────────────┘    
                                    │                                        
                                    ▼                                        
  ┌─────────────────────────────────────────────────────────────────────┐    
  │  STEP 4: THINK (Continue Reasoning)                                 │    
  │  "I found 2 pending transactions. Now I need to flag them."         │    
  └─────────────────────────────────┬───────────────────────────────────┘    
                                    │                                        
                                    ▼                                        
  ┌─────────────────────────────────────────────────────────────────────┐    
  │  STEP 5: ACT (Tool Call #2)                                         │    
  │  Tool: flag_for_review                                              │    
  │  Args: { transaction_ids: ["TXN-002", "TXN-003"], reason: "..." }   │    
  └─────────────────────────────────┬───────────────────────────────────┘    
                                    │                                        
                       ┌────────────┴────────────┐                           
                       ▼                         │                           
             ┌─────────────────┐                 │                           
             │ POLICY CHECK    │                 │                           
             │ HITL REQUIRED   │◀────────────────┘                           
             │ (Write action)  │                                             
             └────────┬────────┘                                             
                      │                                                      
                      ▼                                                      
             ┌─────────────────┐                                             
             │ HUMAN APPROVAL  │                                             
             │ [Approve][Deny] │                                             
             └────────┬────────┘                                             
                      │ (Approved)                                           
                      ▼                                                      
  ┌─────────────────────────────────────────────────────────────────────┐    
  │  STEP 6: OBSERVE (Final Result)                                     │    
  │  "2 transactions flagged for review."                               │    
  └─────────────────────────────────┬───────────────────────────────────┘    
                                    │                                        
                                    ▼                                        
  ┌─────────────────────────────────────────────────────────────────────┐    
  │  STEP 7: RESPOND (Final Answer)                                     │    
  │  "Found 3 high-risk Acme transactions over $10k.                    │    
  │   2 were pending and have been flagged for review: TXN-002, TXN-003"│    
  └─────────────────────────────────────────────────────────────────────┘    
                                                                             
```

════════════════════════════════════════════════════════════════════════════════
                         UI FEATURES
════════════════════════════════════════════════════════════════════════════════
```
┌────────────────────────────────────────────────────────────────────────────┐
│ FEATURE                          │ GRADIO COMPONENT                        │
├──────────────────────────────────┼─────────────────────────────────────────┤
│ Chat Interface                   │ Streaming response                      │
│ Role Selector                    │ Analyst/anager/Compliance/Admin         │
│ Model Selector                   │ GPT-4o/Claude                           │
│ Quick Query Buttons              │ Pre-fill query                          │
│ MCP Tool Call Visualization      │ JSON + phases (what MCP received/sent)  │
│ Audit Log                        │ Auto-updating                           │
│ Results Table                    │ Transaction data                        │
│ HITL Approval Panel              │ Approve/Deny buttons                    │
│ Permissions Display              │ Role-based                              │
└──────────────────────────────────┴─────────────────────────────────────────┘
```

────────────────────────────────────────────────────
MCP : Transaction Search Agent Demo (React)  
────────────────────────────────────────────────────
Features:                                          
• Natural language query input      
• Every tool call is structured, auditable, reproducible
• GOVERNANCE phase intercepts before HIGH-RISK sensitive data is returned
• Human-in-the-loop for HIGH-RISK data - Code/Approval

• Add comprehensive transaction data including edge cases
• Masked card numbers (****1234)                   
• Sample queries for quick testing

• Real-time audit log panel       
• MCP "tool call" visualization panel (show what MCP received/sent)
• Governance controls sidebar

────────────────────────────────────────────────────

```
MCP "tool call" visualization panel:

──────────────────────────────────────────────────────────────────────────
 PHASE         │ COLOR   │ WHAT IT SHOWS                                  
───────────────┼─────────┼────────────────────────────────────────────────
 REQUEST       │ Blue    │ User's natural language query                  
 REASONING     │ Yellow  │ Agent's internal thought process               
 MCP_REQUEST   │ Green   │ JSON-RPC call to MCP server (tool + arguments) 
 MCP_RESPONSE  │ Dk Green│ JSON-RPC response with transaction data        
 GOVERNANCE    │ Red     │ Approval required (high-risk data)             
 APPROVAL      │ Orange  │ User's approve/deny decision                   
 COMPLETE      │ Gray    │ Final agent response metadata                  
──────────────────────────────────────────────────────────────────────────
```
