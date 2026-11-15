
UNIVERSAL LEARNING PROMPT (BEGINNER → ENTERPRISE)
--------------------------------------------------------------------------------

- CHUNKS GENERATED        : [3 / 8]
- ACTIVE CHUNK            : [4 / 8]
- SECTIONS IN THIS CHUNK  : [§05]

### Recommended chunk breakdown

    ```
    ┌───────┬───────────┬──────────────────────────────────────────┬─────────┐
    │ Chunk │ Sections  │ Content Focus                            │ Risk    │
    ├───────┼───────────┼──────────────────────────────────────────┼─────────┤
    │   1   │ §00 – §01 │ Prerequisites + Define                   │ Low     │
    │   2   │ §02 – §03 │ Why It Matters + Core Concepts           │ Low     │
    │   3   │ §04       │ How It Works (sequence diagram)          │ Medium  │
    │   4   │ §05       │ Basic Example (full code, all containers)│ HIGH    │
    │   5   │ §06       │ Intermediate Level (bidirectional tool)  │ HIGH    │
    │   6   │ §07       │ Advanced Concepts (security/scale/perf)  │ Medium  │
    │   7   │ §08 – §12 │ Enterprise + Best Practices + Case Study │ Medium  │
    │       │           │ + Comparison + Common Mistakes           │         │
    │   8   │ §13 – §18 │ Exercises + Quiz + Debugging + Next +    │ Low     │
    │       │           │ Interview + Summary                      │         │
    └───────┴───────────┴──────────────────────────────────────────┴─────────┘
    ```


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

**[MCP SERVER WITH STREAMABLE HTTP TRANSPORT]**

- You are teaching me a structured tutorial from beginner to enterprise level.
- Full bidirectional communication + streaming responses.
- Multi-turn elicitation inside a single tool call.
- Tool 1: server → client chunk streaming.
- Tool 2: same-request bidirectional interaction
  (batch rows → progress → elicit → client replies
  continue/stop + new batch size → server resumes).
- Separate client container.

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
