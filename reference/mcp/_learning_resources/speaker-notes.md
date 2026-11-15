# SPEAKER NOTES: Agentic AI in Fintech
## Full Script with Timing & Transitions

---

# SLIDE 1: Title Slide
**[TIME: 0:00 - 0:30 | 30 seconds]**

### What to Say:
> "Good [morning/afternoon] everyone. Thank you for joining.
>
> Today I'm going to show you something that I believe will change
> how we think about AI at American Express.
>
> We're moving beyond chatbots. We're moving into **agents** —
> AI that doesn't just answer questions, but actually **does work**.
>
> And I have a live demo to prove it."

### Stage Direction:
- Make eye contact with the room
- Pause after "does work" for emphasis

---

# SLIDE 2: Opening Hook
**[TIME: 0:30 - 2:00 | 90 seconds]**

### What to Say:
> "Let me start with a question.
>
> How many of you have seen a support agent spend 5 minutes
> navigating three different systems just to look up a transaction?
>
> [PAUSE — let hands go up]
>
> What if that same agent could just type:
> 'Show me all transactions over $5,000 for Acme Corp in the last week'
> ...and get an instant, compliant, audited answer?
>
> [CLICK — show demo screenshot]
>
> This is what I built. This is what we're going to explore today.
> Not a concept. Not a roadmap. A working demo."

### Stage Direction:
- Rhetorical question — pause for effect
- Point to the screenshot when you show it
- Emphasize "working demo"

---

# SLIDE 3: Agenda
**[TIME: 2:00 - 2:30 | 30 seconds]**

### What to Say:
> "Here's our roadmap for the next 28 minutes.
>
> First, I'll explain the shift from chatbots to agents.
> Then, I'll introduce MCP — the open standard that makes this possible.
> Then, the live demo — you'll see governance in action.
> We'll cover risks and how to mitigate them.
> And I'll propose a concrete next step.
>
> Questions at the end, but feel free to interrupt if something
> is unclear."

### Stage Direction:
- Point to each agenda item as you mention it
- Quick pace — this is a roadmap, not the content

---

# SLIDE 4: The Shift — Chatbot vs. Agent
**[TIME: 2:30 - 7:00 | 4.5 minutes]**

### What to Say:
> "Let's start with the 'why.'
>
> [CLICK — show comparison table]
>
> Most of us have used chatbots. You ask a question, you get an answer.
> Maybe it's helpful, maybe it hallucinates. But that's it.
> The chatbot is **stateless** — it doesn't remember.
> It has **no tools** — it can't query a database or call an API.
> And it requires **human glue** — someone has to take the answer
> and actually do something with it.
>
> [PAUSE]
>
> An **agent** is different.
>
> An agent can **plan**. It can break a task into steps.
> An agent has **memory**. It remembers context across a workflow.
> An agent has **tools**. It can call your APIs, query your databases,
> search your documents.
> And critically — an agent can be **governed**. Every action logged.
> Every sensitive operation gated by human approval.
>
> [PAUSE]
>
> Let me define two terms you'll hear today.
>
> **Agentic AI**: AI that autonomously plans and executes multi-step tasks.
> Not just answering — acting.
>
> **Tool Use**: The ability of an LLM to invoke functions — API calls,
> database queries, system operations — instead of just generating text.
>
> These two concepts are the foundation of everything I'll show you."

### Stage Direction:
- Use hand gestures to contrast "chatbot" (small) vs "agent" (expansive)
- Slow down for the definitions — these are key terms
- Make eye contact with architects and VPs during "governed"

---

# SLIDE 5: Why Now? The MCP Standard
**[TIME: 7:00 - 11:00 | 4 minutes]**

### What to Say:
> "So if agents are so powerful, why aren't we using them everywhere?
>
> The answer, until recently, was integration chaos.
>
> Every AI vendor had their own way of connecting to tools.
> Custom code. Proprietary formats. No standards.
> If you built an integration for one model, you'd have to rebuild
> it for another.
>
> [CLICK — show MCP diagram]
>
> That changed with **MCP** — the Model Context Protocol.
>
> MCP is an **open standard** created by Anthropic and adopted
> across the industry. Think of it as the **USB-C for AI agents**.
>
> [POINT TO DIAGRAM]
>
> Here's how it works:
> - The user sends a natural language request.
> - The LLM agent interprets the request and decides which tool to call.
> - It sends a **standardized MCP request** to an MCP server.
> - The MCP server translates that into your internal API.
> - The response flows back, and the agent generates a human-readable answer.
>
> But here's the key for us at Amex:
>
> [CLICK — next slide]"

### Stage Direction:
- "USB-C for AI agents" — pause for the analogy to land
- Physically point to each step in the diagram

---

# SLIDE 6: MCP in Financial Services Context
**[TIME: 11:00 - 12:00 | 1 minute]**

### What to Say:
> "Why should American Express care about MCP specifically?
>
> [POINT TO TABLE]
>
> **Data Access Control**: MCP lets you define scoped permissions per tool.
> An agent can query transactions but not modify them.
>
> **Audit & Compliance**: Every single tool call is logged with full metadata.
> Who called it, when, with what parameters, what was returned.
>
> **Vendor Lock-in**: MCP is open. If we build integrations today,
> they work with Claude, with GPT, with Gemini, with whatever comes next.
>
> **PII/PCI Handling**: We can mask outputs, require approvals,
> and enforce data minimization — all within the protocol.
>
> This isn't just a technical choice. It's a **governance choice**."

### Stage Direction:
- Emphasize "governance choice" — look at directors/VPs
- Keep this slide crisp — it's a bridge to the demo

---

# SLIDE 7: Live Demo Introduction
**[TIME: 12:00 - 13:00 | 1 minute]**

### What to Say:
> "Enough slides. Let me show you.
>
> [CLICK — show demo introduction]
>
> What you're about to see is a **Transaction Search Agent**.
>
> I'm going to type a natural language query — just like a support agent would.
> The agent will:
> 1. Parse my intent
> 2. Call an MCP tool called `search_transactions`
> 3. Return the results
>
> But I've added three governance features you need to watch for:
>
> **One**: Card numbers are masked. You'll see `****1234`, not full PANs.
>
> **Two**: There's an audit log on the right. Every action is recorded.
>
> **Three**: If my query returns high-risk data, the agent will **stop**
> and ask for my approval before showing results.
>
> Let's do it."

### Stage Direction:
- Build anticipation — this is the payoff
- Count off the three features on your fingers
- Transition to live demo

---

# SLIDE 8: LIVE DEMO
**[TIME: 13:00 - 23:00 | 10 minutes]**

### Demo Script:

#### Query 1: Basic Search (2 min)
> "Let me start simple.
>
> [TYPE]: 'List all pending transactions'
>
> [CLICK SEARCH]
>
> Watch the **Tool Call panel** on the right.
>
> [POINT TO TOOL PANEL]
>
> You can see the agent's reasoning: 'Parsing query to extract filters...'
> Then the **MCP_REQUEST** — this is the actual JSON-RPC call.
> Notice the structure: `method: tools/call`, `params: search_transactions`.
>
> And here's the **MCP_RESPONSE** — the raw data from our API.
>
> The agent then formats this into a human-readable table.
> Two pending transactions. No approval needed — this isn't high-risk data."

---

#### Query 2: High-Risk Trigger (3 min)
> "Now let's try something more sensitive.
>
> [TYPE]: 'Show all transactions over $5,000 for Acme Corp'
>
> [CLICK SEARCH]
>
> [POINT TO GOVERNANCE PANEL]
>
> See what happened? The agent **stopped**.
>
> It detected that this query returns HIGH-RISK transactions.
> Instead of showing the data, it's asking me: 'Approve access?'
>
> This is **Human-in-the-Loop** — or HITL.
>
> The agent is smart enough to take action, but governed enough
> to pause when the stakes are high.
>
> [CLICK APPROVE]
>
> Now I see the results. And look at the audit log:
> `APPROVAL_REQUIRED`, then `ACCESS_APPROVED`.
>
> If this were a real system, that log would be immutable,
> timestamped, and tied to my identity."

---

#### Query 3: Denial Flow (2 min)
> "What if I deny the request?
>
> [TYPE]: 'Find high-risk transactions'
>
> [CLICK SEARCH]
>
> [WAIT FOR APPROVAL MODAL]
>
> This time, I'll click **Deny**.
>
> [CLICK DENY]
>
> The agent respects my decision. Query cancelled.
> Audit log shows `ACCESS_DENIED`.
>
> No data leaked. No unauthorized access. Full traceability."

---

#### Query 4: Show MCP Structure (2 min)
> "Let me highlight the MCP structure one more time.
>
> [TYPE]: 'Show declined transactions over $10,000'
>
> [CLICK SEARCH]
>
> [POINT TO MCP_REQUEST IN TOOL PANEL]
>
> Look at this JSON-RPC request:
> ```
> {
>   "method": "tools/call",
>   "params": {
>     "name": "search_transactions",
>     "arguments": {
>       "min_amount": "10000",
>       "status": "DECLINED"
>     }
>   }
> }
> ```
>
> This is **exactly** what gets sent to the MCP server.
> It's standardized. It's auditable. It's reproducible.
>
> If there's ever a compliance question — 'What did the agent do?' —
> we have the answer. Right here."

---

#### Wrap-Up (1 min)
> "So that's the demo.
>
> Natural language in. Governed, audited, structured actions out.
>
> No code changes to the underlying transaction API.
> MCP is the adapter layer.
>
> Questions so far? [BRIEF PAUSE]
>
> Let me show you how we manage the risks."

### Stage Direction:
- SLOW DOWN during the demo — let people absorb
- Point to specific UI elements as you mention them
- Make eye contact after each query completes
- Brief pause for questions before moving on

---

# SLIDE 9: Governance Framework
**[TIME: 23:00 - 25:00 | 2 minutes]**

### What to Say:
> "What you just saw wasn't magic. It was **design**.
>
> [CLICK — show 4 pillars]
>
> We built this demo around four governance pillars:
>
> **Access Control**: Every tool has scoped permissions.
> The agent can read transactions but not modify them.
> We define what actions are allowed at the MCP server level.
>
> **Auditability**: Every action is logged.
> Who queried, what they queried, when, and what was returned.
> This is non-negotiable for SOX, PCI, and our internal policies.
>
> **Human-in-the-Loop**: Sensitive operations require approval.
> The agent proposes. The human disposes.
> This is configurable — we can define which actions require HITL.
>
> **Output Validation**: Guardrails on what the agent can say.
> No hallucinated account numbers. No fabricated transactions.
> We ground every response to real data."

### Stage Direction:
- Emphasize each pillar name
- "Non-negotiable" — firm tone

---

# SLIDE 10: Risk Matrix
**[TIME: 25:00 - 27:00 | 2 minutes]**

### What to Say:
> "Let me be direct about the risks.
>
> [CLICK — show risk matrix]
>
> **Hallucination**: The agent invents data that doesn't exist.
> Mitigation: Ground every response to real database results.
> In our demo, the agent can't say a transaction exists unless
> it actually returned from the search.
>
> **Unauthorized Access**: The agent accesses data it shouldn't.
> Mitigation: Scoped permissions plus Human-in-the-Loop.
> Even if the agent tries, the MCP server enforces boundaries.
>
> **PII/PCI Exposure**: Sensitive data appears in logs or responses.
> Mitigation: Masking at the MCP layer. You saw `****1234` in the demo.
> Full PANs never reach the agent.
>
> **Prompt Injection**: A malicious user manipulates the agent.
> Mitigation: Input validation, sandboxed execution, and we never
> give the agent write access in early deployments.
>
> **Compliance Violation**: The agent does something auditors hate.
> Mitigation: Pre-approved tool catalog. We define exactly which
> tools the agent can use. Nothing else."

### Stage Direction:
- Direct, confident tone — you've thought about this
- Pause after each risk/mitigation pair

---

# SLIDE 11: Compliance Alignment
**[TIME: 27:00 - 27:30 | 30 seconds]**

### What to Say:
> "Here's how this maps to our compliance requirements.
>
> [POINT TO TABLE]
>
> PCI-DSS: Masked card data, access logging. ✓
> SOX: Audit trails, approval workflows. ✓
> GDPR/CCPA: Data minimization, consent tracking. ✓
> Internal Policy: Role-based access, session-bound auth. ✓
>
> This isn't a 'move fast and break things' approach.
> This is 'move deliberately and stay compliant.'"

### Stage Direction:
- Quick slide — reinforce that you've done the homework
- Checkmarks should feel like a checklist completed

---

# SLIDE 12: Adoption Roadmap
**[TIME: 27:30 - 29:00 | 1.5 minutes]**

### What to Say:
> "So how do we actually adopt this?
>
> [CLICK — show Crawl/Walk/Run]
>
> I recommend a three-phase approach.
>
> **CRAWL**: Start with internal tools. Low-risk use cases.
> Single-tool agents in dev and QA environments.
> This is where we learn — what works, what breaks, what scares people.
>
> **WALK**: Move to customer-facing assistance, but supervised.
> Multi-tool agents that can chain operations.
> Limited production deployment. Human review of every session.
>
> **RUN**: Autonomous workflows for high-value tasks.
> Cross-system orchestration. Full production.
> By this point, we've earned trust through crawl and walk.
>
> I'm proposing we start with CRAWL. Today. With a specific use case."

### Stage Direction:
- Build from cautious to ambitious
- "Today" — direct call to action

---

# SLIDE 13: Suggested Pilot
**[TIME: 29:00 - 29:30 | 30 seconds]**

### What to Say:
> "The pilot I'm proposing is exactly what you saw in the demo.
>
> **Transaction Search for Support Agents**.
>
> Risk level: Low — it's read-only with masked data.
> Integration: MCP to our existing transaction API.
> Governance: Audit log plus Human-in-the-Loop for high-risk queries.
> Timeline: 6 to 8 weeks for a working POC.
> Success metric: 40% reduction in transaction lookup time.
>
> This is small enough to be safe. Big enough to prove the concept."

### Stage Direction:
- Confident, specific — you have a plan
- Pause after "40% reduction"

---

# SLIDE 14: Architecture Overview
**[TIME: 29:30 - 30:00 | 30 seconds]**

### What to Say:
> "[CLICK — show architecture diagram]
>
> Here's how this fits into our infrastructure.
>
> User talks to Claude. Claude talks to our MCP Gateway.
> The gateway routes to internal services — transaction API,
> audit service, IAM.
>
> The MCP Gateway is our control point. That's where we enforce
> permissions, log actions, and mask sensitive data.
>
> This doesn't require rearchitecting our core systems.
> MCP is an adapter layer."

### Stage Direction:
- Point to each component
- Emphasize "doesn't require rearchitecting"

---

# SLIDE 15: Key Takeaways
**[TIME: 30:00 - 30:30 | 30 seconds]**

### What to Say:
> "Four things I want you to remember:
>
> **One**: Agentic AI is not a chatbot. It takes actions.
>
> **Two**: MCP gives us a standard way to integrate — auditable,
> secure, vendor-neutral.
>
> **Three**: Governance is built in, not bolted on.
> Audit logs, Human-in-the-Loop, masked data.
>
> **Four**: We can start small. Transaction search is the pilot."

### Stage Direction:
- Count off on fingers
- Eye contact with leadership on "start small"

---

# SLIDE 16: Call to Action
**[TIME: 30:30 - 31:00 | 30 seconds]**

### What to Say:
> "Here's what I'm asking for.
>
> [POINT TO TABLE]
>
> Step 1: Form a working group — engineering and risk together.
> Step 2: Define the pilot scope and success metrics with architecture.
> Step 3: Security review of MCP integration with InfoSec.
> Step 4: Six-week POC build.
> Step 5: Present results to leadership.
>
> I'd like to schedule a follow-up meeting this week to kick off
> Step 1.
>
> Who's in?"

### Stage Direction:
- Direct ask — look at decision-makers
- Pause after "Who's in?" — wait for response

---

# SLIDE 17: Q&A
**[TIME: 31:00+ | Open]**

### What to Say:
> "That's the presentation. I'll leave this up.
>
> Questions?"

### Anticipated Questions & Answers:

**Q: What if the agent hallucinates transaction data?**
> "It can't — by design. The agent only surfaces data that comes from
> the MCP tool response. It doesn't generate transaction IDs or amounts.
> If the database doesn't return it, the agent doesn't say it."

**Q: How do we handle PII in logs?**
> "Masking happens at the MCP Gateway layer, before data reaches the agent.
> Audit logs contain masked values only. Full PANs never appear anywhere
> the agent or logs can see."

**Q: What's the cost?**
> "For the pilot, primarily engineering time — 6 weeks for 2-3 engineers.
> API costs for Claude are usage-based; for a read-only transaction search,
> we're talking about a few hundred dollars per month during pilot.
> We can refine estimates after the POC."

**Q: What if the agent is asked to do something it shouldn't?**
> "Two layers. First, the MCP server only exposes approved tools.
> The agent literally cannot call a function that doesn't exist.
> Second, Human-in-the-Loop catches anything we flag as sensitive.
> Belt and suspenders."

**Q: Why MCP instead of building our own?**
> "Standards beat custom. MCP is adopted by Anthropic, OpenAI,
> Google, and others. If we build on MCP, our integrations work
> across models. If we build custom, we're locked in and maintaining
> our own protocol forever."

---

# END OF SCRIPT

## Pre-Presentation Checklist:
- [ ] Demo loaded and tested
- [ ] Sample queries work
- [ ] Tool panel visible
- [ ] Audit log visible
- [ ] Internet connection stable (if using live API)
- [ ] Backup screenshots ready (in case demo fails)

## Post-Presentation:
- [ ] Send deck + demo link to attendees
- [ ] Schedule working group kickoff
- [ ] Document questions raised
- [ ] Follow up with stakeholders 1:1
