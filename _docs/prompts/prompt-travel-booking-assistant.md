Teach me, from first principles, how an MCP-based generative-UI (gen-UI) system
works, using a "Travel Booking Assistant" use case (flights + hotels) as the
running example throughout.

**Important scope constraint:**

1. Do NOT focus on business logic that generates real flight/hotel data (
   pricing, availability, search algorithms, etc.)
2. **Stub all data** with small hardcoded/mock JSON payloads.
3. The focus is entirely on the **protocol, tool-calling, and rendering
   mechanics** — not the domain logic.

### Use this use case to walk through both flows:

1. **Flow 1 (request path):**
   `User Language → LLM interprets intent → MCP tool call → structured content → gen-ui widget renders`

   **Example:** "Find me a flight from Delhi to Goa next Friday" → LLM extracts
   intent/params → calls `search_flights` MCP tool (returns stubbed mock data) →
   UI renders a flight list widget. Same pattern for `search_hotels`.

2. **Flow 2 (interaction path):**
   `Widget → user action → UI JS → MCP tool call → structured content → UI re-renders`

   **Example:** user clicks "Select Fare"/"Select Room" → UI JS captures the
   click → calls `select_fare`/`select_room` MCP tool (stubbed response) →
   widget re-renders with new state.

### **Integration sequencing (important):**

1. First teach and demonstrate the MCP server + gen-ui widget integrated with
   ChatGPT (as the MCP client/host).

2. Only after that flow works end-to-end, teach the equivalent integration with
   Claude (as the MCP client/host), highlighting what stays the same (the MCP
   server, tools, structured content) vs. what differs (client-specific setup,
   connector/config, any host-specific UI rendering rules).

### **Requirements:**

- Teach **one concept at a time**, in dependency order (don't skip ahead to
  frameworks before I understand the underlying idea).

- For each concept: explain what it is, why it matters, how it builds on the
  previous concept **using the travel booking use case as illustration**, and
  give one small hands-on task (code/command I can run) before moving on.

- Cover enough **depth** (why the protocol/design choice exists, tradeoffs) and
  **breadth** (how the concept connects to the full
  request→render→action→re-render loop).

- Don't advance to the next concept until I respond or explicitly ask to
  continue.

- Assume I don't yet know MCP, tool calling, or gen-ui widget rendering — build
  from basics
  (LLM tool calling → MCP protocol → structured content → UI rendering → event
  loop back to the LLM).
