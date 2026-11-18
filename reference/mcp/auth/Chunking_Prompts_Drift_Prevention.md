Review the attached [prompt].

### Problem

- Running all sections in one prompt causes context drift
- Models lose instruction fidelity after ~8–10k tokens
- Tables get skipped
- Sections get merged
- Depth drops.

### Goal:

- Anchor the model
- Force maximum detail/depth
- Prevent context drift
- Prevent hallucinations

### ASK

Recommended a chunk breakdown:

- Each chunk is small enough to hold all formatting rules in context.
- Each chunk artifact is self-contained but logically ordered.
- I should be able to review and re-run one chunk if quality drops without
  redoing everything.

```
UNIVERSAL LEARNING PROMPT (BEGINNER → ENTERPRISE)
--------------------------------------------------------------------------------

## CHUNKS GENERATED: [0 / N]

## ACTIVE CHUNK: [1 / N]

## SECTIONS IN THIS CHUNK: [§00, §01]

## OUTPUT FORMAT RULES (STRICT: NON-NEGOTIABLE)

- Follow for every section
- Use `##` headers for each section.
- Use numbered steps for all sequences.
- Use tables for comparisons and structured data.
- Use fenced code blocks for ALL code.
- Max 80 characters per line. Wrap gracefully.
- **Bold** all jargon terms on first use.
- Add a diagram or table to every section that benefits from one.
- Use mermaid diagram when it's the best choice
- When mermaid is not the best choice, alternative must be compatible with
  markdown files
- Do not skip any section.
- Do not combine sections.

--------------------------------------------------------------------------------

## IMPLEMENTATION (STRICT: NON-NEGOTIABLE)

- Language: **[Python(uv), uvicorn, PostgreSQL]**
- Include seed data script with at-lest 100 records
- Use structured logging
- Use OpenAI LLM as default where applicable
- Use LiteLLM to allow swapping other models
- Use OpenAI Agent SDK where applicable
- Use MCP (SDK) where possible
- Use FastAPI Gateway
- Apply enterprise design patterns
- Write modular code
- Run inside Docker unless it's not possible.
- Use Clean architecture
- Use Ports and Adapters for DB calls
- Use latest stable versions of dependencies
- Use Ngnix reverse proxy
- Follow this exact structure:
    1. Setup and install dependencies
    2. Write the core logic
    3. Run and verify output
- Explain every line with inline comments.
- Show the exact expected output.
- Add a step-by-step flow diagram of the code logic.

--------------------------------------------------------------------------------

## TOPIC

- You are teaching me a structured **[MCP SERVER WITH STREAMABLE HTTP
  TRANSPORT]** tutorial from beginner to enterprise level.
- HTTP transport must uses the Streamable HTTP protocol,
  which supports full bidirectional communication and streaming responses.
- It must also supports multi-turn elicitation inside a tool call, so the server
  can pause, ask the client for more input, then continue the same tool
  execution.
- One tool for server -> client chunk streaming
- One tool for same-request bidirectional interaction
- Separate client container
- Follow all formatting rules strictly.

What the bidirectional tool does:

- server sends a batch of rows as a streamed log chunk
- server sends progress updates
- server calls `ctx.elicit(...)`
- client replies with `continue` or `stop`, and can change the next batch size
- server resumes the same request and sends the next batch

### Recommended chunk breakdown

    ```
    ┌───────┬───────────────────┐
    │ Chunk │    Sections       │
    ├───────┼───────────────────┤
    │   1   │    §00 – §00      │  
    │   2   │    §00 – §00      │
    │   3   │    §00 – §00      │
    │   4   │    §00 – §00      │
    │   5   │    §00 – §00      │
    │   6   │    §00 – §00      │
    │   7   │    §00 – §00      │
    │   8   │    §00 – §00      │
    └───────┴───────────────────┘
    ```

--------------------------------------------------------------------------------


## 0. PREREQUISITES

- List what I must already know before learning this.
- Rate the required knowledge:
  Beginner / Intermediate / Advanced
- List 2–3 concepts to study first if I am missing them.
- Estimate time to learn this topic end-to-end.

--------------------------------------------------------------------------------

## 1. DEFINE

- Give a short, precise definition (2–3 sentences max).
- List all key terms with short definitions.
- **Bold** every jargon term.
- Provide a one-line definition for each jargon term.
- Add a table:
    ```
    ┌──────────────────┬─────────────────────┬─────────────────────┐
    │ Term             │ Definition          │ Why it matters      │
    ├──────────────────┼─────────────────────┼─────────────────────┤
    │                  │                     │                     │  
    │                  │                     │                     │
    └──────────────────┴─────────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 2. WHY IT MATTERS

- Explain the real-world purpose.
- List where it is used in the industry.
- Give exactly 3 concrete use cases.
- Add a table:
    ```
    ┌──────────────────┬─────────────────────┬─────────────────────┐
    │ Use Case         │ Idustry             │ Problem it Solves   │
    ├──────────────────┼─────────────────────┼─────────────────────┤
    │                  │                     │                     │  
    │                  │                     │                     │
    └──────────────────┴─────────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 3. CORE CONCEPTS (FOUNDATION)

- List all topics
- Explain each topic in depth
- Break the topic into small building blocks.
- Explain each block step-by-step.
- Use a simple example for each block.
- Add a flow diagram or table showing how blocks
  connect.

--------------------------------------------------------------------------------

## 4. HOW IT WORKS (MECHANISM)

- Show the internal working step-by-step.
- Do not skip any step.
- Add a block diagram or sequence diagram.
- Label every part of the diagram.

--------------------------------------------------------------------------------

## 5. BASIC EXAMPLE

- Solve one simple end-to-end example.
- Show every step clearly.
- Show expected input and expected output.
- Add inline code comments explaining each line.

--------------------------------------------------------------------------------

## 6. INTERMEDIATE LEVEL

- Show a more complex real-world example.
- Add a diagram showing the added complexity.
- List 3–5 edge cases with explanations.
- List 3 key limitations.
- Add a table:
    ```
    ┌──────────────────┬─────────────────────┬─────────────────────┐
    │ Scenario         │ Behavior            │ Why                 │
    ├──────────────────┼─────────────────────┼─────────────────────┤
    │                  │                     │                     │  
    │                  │                     │                     │
    └──────────────────┴─────────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 7. ADVANCED CONCEPTS

Cover all the following sub-topics:

### Security

- Basic protections
- Advanced protections
- Common vulnerabilities and fixes

### Scaling

- Load balancing
- Caching strategies
- Sharding

### Reliability

- Fault tolerance
- Replication
- Recovery strategies

### Optimization

- Performance improvements
- Bottleneck identification

### Trade-offs

- Add a table:
    ```
    ┌──────────────────┬─────────────┬─────────────────┬─────────────────────┐
    │ Approach         │ Pros        │ Cons            │ When to use         │
    ├──────────────────┼─────────────┼─────────────────┼─────────────────────┤
    │                  │             │                 │                     │  
    │                  │             │                 │                     │
    └──────────────────┴─────────────┴─────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 8. ENTERPRISE USAGE

- Explain how real companies use this in production.
- Give exactly 2–3 real company examples.
- Show an architecture diagram for each example.
- List tools, frameworks, and patterns used.
- Add a table:
    ```
    ┌────────────┬───────────────────┬─────────────────┬─────────────────────┐
    │ Company    │ How they use it   │ Scale           │ Tools used          │
    ├────────────┼───────────────────┼─────────────────┼─────────────────────┤
    │            │                   │                 │                     │  
    │            │                   │                 │                     │
    └────────────┴───────────────────┴─────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 9. BEST PRACTICES

- List industry-standard rules.
- Explain why each rule exists.
- Flag what happens if the rule is broken.
- Add a table:
    ```
    ┌──────────────────┬─────────────────────┬─────────────────────┐
    │ Practice         │ Reaason             │ Risk if ignored     │
    ├──────────────────┼─────────────────────┼─────────────────────┤
    │                  │                     │                     │  
    │                  │                     │                     │
    └──────────────────┴─────────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 10. CASE STUDY

- Pick one real company example.
- Use this structure:
    1. Company and context
    2. Problem they faced
    3. Solution they implemented
    4. Result / outcome
    5. Lessons learned
- Add an architecture or flow diagram.

--------------------------------------------------------------------------------

## 11. COMPARISON

- Compare this concept with 2–3 related concepts.
- Add a table:
    ```
    ┌────────────┬───────────────────┬─────────────────┬─────────────────────┐
    │ Feature    │ This concept      │ Alternative 1   │ Alternative 2       │
    ├────────────┼───────────────────┼─────────────────┼─────────────────────┤
    │            │                   │                 │                     │  
    │            │                   │                 │                     │
    └────────────┴───────────────────┴─────────────────┴─────────────────────┘
    ```

- Include: differences, pros, cons, when to use each.

--------------------------------------------------------------------------------

## 12. COMMON MISTAKES

- List the 5 most frequent beginner errors.
- For each mistake:
    - What the mistake is
    - Why it happens
    - How to fix it
- Add a table:
    ```
    ┌────────────┬───────────────────┬──────────────────┐
    │ Mistake    │ Cause             │ Fix              │
    ├────────────┼───────────────────┼──────────────────┤
    │            │                   │                  │  
    │            │                   │                  │
    └────────────┴───────────────────┴──────────────────┘
    ```

--------------------------------------------------------------------------------

## 13. PRACTICE EXERCISES

Give exactly 3 exercises. For each:

- State the task clearly.
- List constraints or requirements.
- State what a correct solution looks like.

### Easy

### Medium

### Hard

--------------------------------------------------------------------------------

## 14. CHECK UNDERSTANDING

Ask me exactly 5 questions to test my understanding.
Cover: definition, mechanism, application, trade-offs,
and a scenario-based question.

--------------------------------------------------------------------------------

## 15. DEBUGGING

- List the 5 most common bugs for this topic.
- For each bug add a table row:
    ```
    ┌────────────┬───────────────────┬─────────────────┬─────────────────────┐
    │ Bug        │ Cause             │ Error message   │ Fix                 │
    ├────────────┼───────────────────┼─────────────────┼─────────────────────┤
    │            │                   │                 │                     │  
    │            │                   │                 │                     │
    └────────────┴───────────────────┴─────────────────┴─────────────────────┘
    ```

- Show a broken code example.
- Show the fixed version side by side.
- Explain why each bug happens.

--------------------------------------------------------------------------------

## 16. WHAT TO LEARN NEXT

- List 3 related concepts to study after this.
- For each concept:
    - Why it builds on what I just learned
    - Difficulty level
- Suggest 1–2 tools or platforms to practice with.
- Suggest 1 project I can build to reinforce this topic.
- Add a table:
    ```
    ┌────────────┬───────────────────┬─────────────────┐
    │ Next Topic │ Why it matters    │ Difficulty      │
    ├────────────┼───────────────────┼─────────────────┤
    │            │                   │                 │  
    │            │                   │                 │
    └────────────┴───────────────────┴─────────────────┘
    ```

--------------------------------------------------------------------------------

## 17. INTERVIEW QUESTIONS

List questions from beginner to advanced.
For each question provide a short, direct answer.

### Beginner (3–5 questions)

### Intermediate (3–5 questions)

### Advanced (3–5 questions)

### System design / enterprise (2–3 questions)

--------------------------------------------------------------------------------

## 18. SUMMARY (REINFORCEMENT)

- Bullet all key points from every section.
- List all jargon terms introduced (bolded).
- Repeat the 5 most important concepts to memorize.
- Add a table:
    ```
    ┌────────────┬───────────────────┐
    │ Concept    │ One-line reminder │
    ├────────────┼───────────────────┤
    │            │                   │  
    │            │                   │
    └────────────┴───────────────────┘
    ```

## 0. PREREQUISITES

- List what I must already know before learning this.
- Rate the required knowledge:
  Beginner / Intermediate / Advanced
- List 2–3 concepts to study first if I am missing them.
- Estimate time to learn this topic end-to-end.

--------------------------------------------------------------------------------

## 1. DEFINE

- Give a short, precise definition (2–3 sentences max).
- List all key terms with short definitions.
- **Bold** every jargon term.
- Provide a one-line definition for each jargon term.
- Add a table:
    ```
    ┌──────────────────┬─────────────────────┬─────────────────────┐
    │ Term             │ Definition          │ Why it matters      │
    ├──────────────────┼─────────────────────┼─────────────────────┤
    │                  │                     │                     │  
    │                  │                     │                     │
    └──────────────────┴─────────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 2. WHY IT MATTERS

- Explain the real-world purpose.
- List where it is used in the industry.
- Give exactly 3 concrete use cases.
- Add a table:
    ```
    ┌──────────────────┬─────────────────────┬─────────────────────┐
    │ Use Case         │ Idustry             │ Problem it Solves   │
    ├──────────────────┼─────────────────────┼─────────────────────┤
    │                  │                     │                     │  
    │                  │                     │                     │
    └──────────────────┴─────────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 3. CORE CONCEPTS (FOUNDATION)

- List all topics
- Explain each topic in depth
- Break the topic into small building blocks.
- Explain each block step-by-step.
- Use a simple example for each block.
- Add a flow diagram or table showing how blocks
  connect.

--------------------------------------------------------------------------------

## 4. HOW IT WORKS (MECHANISM)

- Show the internal working step-by-step.
- Do not skip any step.
- Add a block diagram or sequence diagram.
- Label every part of the diagram.

--------------------------------------------------------------------------------

## 5. BASIC EXAMPLE

- Solve one simple end-to-end example.
- Show every step clearly.
- Show expected input and expected output.
- Add inline code comments explaining each line.

--------------------------------------------------------------------------------

## 6. INTERMEDIATE LEVEL

- Show a more complex real-world example.
- Add a diagram showing the added complexity.
- List 3–5 edge cases with explanations.
- List 3 key limitations.
- Add a table:
    ```
    ┌──────────────────┬─────────────────────┬─────────────────────┐
    │ Scenario         │ Behavior            │ Why                 │
    ├──────────────────┼─────────────────────┼─────────────────────┤
    │                  │                     │                     │  
    │                  │                     │                     │
    └──────────────────┴─────────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 7. ADVANCED CONCEPTS

Cover all the following sub-topics:

### Security

- Basic protections
- Advanced protections
- Common vulnerabilities and fixes

### Scaling

- Load balancing
- Caching strategies
- Sharding

### Reliability

- Fault tolerance
- Replication
- Recovery strategies

### Optimization

- Performance improvements
- Bottleneck identification

### Trade-offs

- Add a table:
    ```
    ┌──────────────────┬─────────────┬─────────────────┬─────────────────────┐
    │ Approach         │ Pros        │ Cons            │ When to use         │
    ├──────────────────┼─────────────┼─────────────────┼─────────────────────┤
    │                  │             │                 │                     │  
    │                  │             │                 │                     │
    └──────────────────┴─────────────┴─────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 8. ENTERPRISE USAGE

- Explain how real companies use this in production.
- Give exactly 2–3 real company examples.
- Show an architecture diagram for each example.
- List tools, frameworks, and patterns used.
- Add a table:
    ```
    ┌────────────┬───────────────────┬─────────────────┬─────────────────────┐
    │ Company    │ How they use it   │ Scale           │ Tools used          │
    ├────────────┼───────────────────┼─────────────────┼─────────────────────┤
    │            │                   │                 │                     │  
    │            │                   │                 │                     │
    └────────────┴───────────────────┴─────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 9. BEST PRACTICES

- List industry-standard rules.
- Explain why each rule exists.
- Flag what happens if the rule is broken.
- Add a table:
    ```
    ┌──────────────────┬─────────────────────┬─────────────────────┐
    │ Practice         │ Reaason             │ Risk if ignored     │
    ├──────────────────┼─────────────────────┼─────────────────────┤
    │                  │                     │                     │  
    │                  │                     │                     │
    └──────────────────┴─────────────────────┴─────────────────────┘
    ```

--------------------------------------------------------------------------------

## 10. CASE STUDY

- Pick one real company example.
- Use this structure:
    1. Company and context
    2. Problem they faced
    3. Solution they implemented
    4. Result / outcome
    5. Lessons learned
- Add an architecture or flow diagram.

--------------------------------------------------------------------------------

## 11. COMPARISON

- Compare this concept with 2–3 related concepts.
- Add a table:
    ```
    ┌────────────┬───────────────────┬─────────────────┬─────────────────────┐
    │ Feature    │ This concept      │ Alternative 1   │ Alternative 2       │
    ├────────────┼───────────────────┼─────────────────┼─────────────────────┤
    │            │                   │                 │                     │  
    │            │                   │                 │                     │
    └────────────┴───────────────────┴─────────────────┴─────────────────────┘
    ```

- Include: differences, pros, cons, when to use each.

--------------------------------------------------------------------------------

## 12. COMMON MISTAKES

- List the 5 most frequent beginner errors.
- For each mistake:
    - What the mistake is
    - Why it happens
    - How to fix it
- Add a table:
    ```
    ┌────────────┬───────────────────┬──────────────────┐
    │ Mistake    │ Cause             │ Fix              │
    ├────────────┼───────────────────┼──────────────────┤
    │            │                   │                  │  
    │            │                   │                  │
    └────────────┴───────────────────┴──────────────────┘
    ```

--------------------------------------------------------------------------------

## 13. PRACTICE EXERCISES

Give exactly 3 exercises. For each:

- State the task clearly.
- List constraints or requirements.
- State what a correct solution looks like.

### Easy

### Medium

### Hard

--------------------------------------------------------------------------------

## 14. CHECK UNDERSTANDING

Ask me exactly 5 questions to test my understanding.
Cover: definition, mechanism, application, trade-offs,
and a scenario-based question.

--------------------------------------------------------------------------------

## 15. DEBUGGING

- List the 5 most common bugs for this topic.
- For each bug add a table row:
    ```
    ┌────────────┬───────────────────┬─────────────────┬─────────────────────┐
    │ Bug        │ Cause             │ Error message   │ Fix                 │
    ├────────────┼───────────────────┼─────────────────┼─────────────────────┤
    │            │                   │                 │                     │  
    │            │                   │                 │                     │
    └────────────┴───────────────────┴─────────────────┴─────────────────────┘
    ```

- Show a broken code example.
- Show the fixed version side by side.
- Explain why each bug happens.

--------------------------------------------------------------------------------

## 16. WHAT TO LEARN NEXT

- List 3 related concepts to study after this.
- For each concept:
    - Why it builds on what I just learned
    - Difficulty level
- Suggest 1–2 tools or platforms to practice with.
- Suggest 1 project I can build to reinforce this topic.
- Add a table:
    ```
    ┌────────────┬───────────────────┬─────────────────┐
    │ Next Topic │ Why it matters    │ Difficulty      │
    ├────────────┼───────────────────┼─────────────────┤
    │            │                   │                 │  
    │            │                   │                 │
    └────────────┴───────────────────┴─────────────────┘
    ```

--------------------------------------------------------------------------------

## 17. INTERVIEW QUESTIONS

List questions from beginner to advanced.
For each question provide a short, direct answer.

### Beginner (3–5 questions)

### Intermediate (3–5 questions)

### Advanced (3–5 questions)

### System design / enterprise (2–3 questions)

--------------------------------------------------------------------------------

## 18. SUMMARY (REINFORCEMENT)

- Bullet all key points from every section.
- List all jargon terms introduced (bolded).
- Repeat the 5 most important concepts to memorize.
- Add a table:
    ```
    ┌────────────┬───────────────────┐
    │ Concept    │ One-line reminder │
    ├────────────┼───────────────────┤
    │            │                   │  
    │            │                   │
    └────────────┴───────────────────┘
    ```

--------------------------------------------------------------------------------

## COMPLETED SECTIONS

--------------------------------------------------------------------------------

```

## Output

## Key decisions

### Why 8 chunks?
- Sections §05 and §06 are isolated: they contain
  the heaviest code output.
- Merging them causes table skipping and depth loss.

### Why an anchor block?
- Models reset formatting rules per context window.
- Pasting the anchor block forces rule re-loading
  at the start of every chunk.
- The TOPIC REMINDER section prevents semantic drift
  (model forgetting what Tool 2 actually does).

### Why §08–§12 together?
- None contain code.
- All are table-heavy but token-light.
- Grouping them reduces total round trips.

### Re-run strategy
- One chunk = one atomic unit.
- If chunk 5 drifts, re-run chunk 5 only.
- No need to touch chunks 4 or 6.

---

# MCP Streamable HTTP — Chunk Breakdown

## CHUNKS GENERATED: [8 / 8]

---

## Design Rationale

| Rule                        | Target                        |
|-----------------------------|-------------------------------|
| Max tokens per chunk        | ~6,000–7,000 output tokens    |
| Sections per chunk          | 1–3 (never more than 3)       |
| Code-heavy sections         | 1 section per chunk only      |
| Reformatting risk           | Isolated; re-run 1 chunk only |

---

## Chunk Map

```

┌───────┬───────────┬──────────────────────────────────────────┬────────────┐
│ Chunk │ Sections  │ Content Focus                            │ Risk Level │
├───────┼───────────┼──────────────────────────────────────────┼────────────┤
│   1   │ §00 – §01 │ Prerequisites + Define                   │ Low        │
│   2   │ §02 – §03 │ Why It Matters + Core Concepts           │ Low        │
│   3   │ §04       │ How It Works (sequence diagram)          │ Medium     │
│   4   │ §05       │ Basic Example (full code, all containers)│ HIGH       │
│   5   │ §06       │ Intermediate Level (bidirectional tool)  │ HIGH       │
│   6   │ §07       │ Advanced Concepts (security/scale/perf)  │ Medium     │
│   7   │ §08 – §12 │ Enterprise + Best Practices + Case Study │ Medium     │
│       │           │ + Comparison + Common Mistakes           │            │
│   8   │ §13 – §18 │ Exercises + Quiz + Debugging + Next +    │ Low        │
│       │           │ Interview + Summary                      │            │
└───────┴───────────┴──────────────────────────────────────────┴────────────┘
```

---

## Anchor Block (paste at top of EVERY chunk prompt)

```

## ACTIVE CHUNK: [X / 8]

## SECTIONS IN THIS CHUNK: [§XX, §XX]

## OUTPUT FORMAT RULES (NON-NEGOTIABLE — re-read before writing)

- Use ## headers for each section.
- Numbered steps for ALL sequences.
- Tables for ALL comparisons and structured data.
- Fenced code blocks for ALL code.
- Max 80 characters per line.
- **Bold** all jargon on first use.
- Add a diagram or table to every section that benefits from one.
- Use mermaid when it is the best choice.
- Do NOT skip any section.
- Do NOT combine sections.

## IMPLEMENTATION CONSTRAINTS (NON-NEGOTIABLE)

- Language: Python (uv), uvicorn, PostgreSQL
- Docker for all containers
- FastAPI gateway + Nginx reverse proxy
- Clean Architecture + Ports and Adapters
- Structured logging
- LiteLLM + OpenAI default
- OpenAI Agent SDK where applicable
- MCP SDK (Streamable HTTP transport)
- Seed data: minimum 100 records
- Inline comments on every line of code
- Show exact expected output
- Step-by-step flow diagram per code section

## TOPIC REMINDER

MCP Server with Streamable HTTP Transport.

- Full bidirectional communication + streaming responses.
- Multi-turn elicitation inside a single tool call.
- Tool 1: server → client chunk streaming.
- Tool 2: same-request bidirectional interaction
  (batch rows → progress → elicit → client replies
  continue/stop + new batch size → server resumes).
- Separate client container.

```

---

## Per-Chunk Prompts

### Chunk 1 — Sections §00 – §01

```

[PASTE ANCHOR BLOCK]

Now generate ONLY:

- Section 00: Prerequisites
- Section 01: Define

Do NOT generate any other section.

```

---

### Chunk 2 — Sections §02 – §03

```

[PASTE ANCHOR BLOCK]

Sections §00–§01 are COMPLETE. Do not regenerate them.

Now generate ONLY:

- Section 02: Why It Matters
- Section 03: Core Concepts (Foundation)

Do NOT generate any other section.

```

---

### Chunk 3 — Section §04

```

[PASTE ANCHOR BLOCK]

Sections §00–§03 are COMPLETE. Do not regenerate them.

Now generate ONLY:

- Section 04: How It Works (Mechanism)

Requirements:

- Full sequence diagram (mermaid).
- Label every actor: Client, Nginx, FastAPI Gateway,
  MCP Server, PostgreSQL.
- Show both Tool 1 (streaming) and Tool 2
  (bidirectional elicitation) flows.
- Do NOT include code yet.

Do NOT generate any other section.

```

---

### Chunk 4 — Section §05

```

[PASTE ANCHOR BLOCK]

Sections §00–§04 are COMPLETE. Do not regenerate them.

Now generate ONLY:

- Section 05: Basic Example

Requirements:

- Full working code for ALL containers:
  mcp_server, client, fastapi_gateway, nginx.
- docker-compose.yml included.
- Seed script with 100+ records.
- Implement Tool 1 ONLY (streaming).
- Inline comment on every line.
- Show exact expected terminal output.
- Flow diagram of code logic.

Do NOT generate any other section.

```

---

### Chunk 5 — Section §06

```

[PASTE ANCHOR BLOCK]

Sections §00–§05 are COMPLETE. Do not regenerate them.

Now generate ONLY:

- Section 06: Intermediate Level

Requirements:

- Implement Tool 2 ONLY (bidirectional elicitation):
  server sends batch → progress update → ctx.elicit()
  → client replies continue/stop + new batch size
  → server resumes same request.
- Full code for affected files only (diff approach).
- Edge case table (3–5 rows).
- Limitations list (3 items).
- Scenario table.
- Diagram showing elicitation flow.

Do NOT generate any other section.

```

---

### Chunk 6 — Section §07

```

[PASTE ANCHOR BLOCK]

Sections §00–§06 are COMPLETE. Do not regenerate them.

Now generate ONLY:

- Section 07: Advanced Concepts

Cover all sub-topics:
Security, Scaling, Reliability, Optimization,
Trade-offs.

Each sub-topic must have:

- Bullet list of rules/patterns.
- Code snippet if applicable.
- Trade-off table at the end.

Do NOT generate any other section.

```

---

### Chunk 7 — Sections §08 – §12

```

[PASTE ANCHOR BLOCK]

Sections §00–§07 are COMPLETE. Do not regenerate them.

Now generate ONLY:

- Section 08: Enterprise Usage
- Section 09: Best Practices
- Section 10: Case Study
- Section 11: Comparison
- Section 12: Common Mistakes

Each section must have its required table.
No code needed in this chunk.

Do NOT generate any other section.

```

---

### Chunk 8 — Sections §13 – §18

```

[PASTE ANCHOR BLOCK]

Sections §00–§12 are COMPLETE. Do not regenerate them.

Now generate ONLY:

- Section 13: Practice Exercises
- Section 14: Check Understanding (5 questions)
- Section 15: Debugging
- Section 16: What to Learn Next
- Section 17: Interview Questions
- Section 18: Summary (Reinforcement)

Each section must have its required table.

Do NOT generate any other section.

```

---

## Re-run Rule

If quality drops in any chunk:
1. Identify the chunk number.
2. Paste the anchor block fresh.
3. Add: `"Regenerate ONLY chunk X (§XX–§XX).
   All other sections are final."`
4. Do not re-run adjacent chunks.

---

## Summary

| Rule                  | Value                              |
|-----------------------|------------------------------------|
| Total chunks          | 8                                  |
| Max sections/chunk    | 3 (5 only for §08–§12, no code)    |
| Code chunks           | 4 and 5 (isolated, 1 section each) |
| Anchor block required | Every chunk, pasted at top         |
| Re-run scope          | One chunk at a time                |

```