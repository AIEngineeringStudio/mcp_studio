# 🧠 MCP + Gen-UI Learning Notes — Travel Booking Assistant

> Running use case: a "Travel Booking Assistant" (flights + hotels). All flight/hotel data is  
> **stubbed/mocked** — the focus is on the tool-calling and rendering **mechanics**, not business logic.

---

## Concept 1: What "Tool Calling" Means for an LLM

### 1. Plain-language definition

- An LLM (Large Language Model) normally only **outputs text**. It cannot search a flight database, book a hotel, or run
  code by itself.
- **Tool calling** (also called "function calling") is a mechanism where the LLM, instead of just replying with text,
  can say: *"I want to run this specific function, with these specific arguments."*
- The LLM itself never executes the function. It only **requests** it. Some outside program (the "host" or "client")
  actually runs it and gives the result back to the LLM.

### 2. Why it matters

- Without tool calling, if you ask **"Find me a flight from Delhi to Goa next Friday."** the LLM would have to *
  *guess/hallucinate** flight data from its training — which is wrong and outdated.
- Tool calling lets the LLM stay a *reasoning engine* while a **real system** (our stubbed `search_flights` function)
  supplies real (or in our case, mock) data.
- This is the foundational building block behind MCP, agents, and gen-UI — everything else in the two flows below
  depends on this working correctly.

### 3. Building it from prerequisites

- Prerequisite: you already know an LLM takes text in, produces text out.
- New idea: the LLM's output isn't always *text for the human.* It can be **structured text meant for a program** — a
  JSON object describing a function name + arguments.
- The **host application** (e.g., ChatGPT's backend, or your own app) is responsible for:
    1. Telling the LLM which tools exist (name, description, input schema).
    2. Reading the LLM's tool-call request.
    3. Running the actual function.
    4. Feeding the function's result back to the LLM as new input.
    5. Letting the LLM produce a final answer (or another tool call).

### 4. Visual model

```
User: "Find me a flight from Delhi to Goa next Friday"
           |
           v
      +---------+
      |   LLM   | -----> "I need to call search_flights(from=Delhi, to=Goa, date=next Friday)"
      +---------+                                      |
           ^                                           v
           |                                  +----------------------+
           |                                  | Host runs the actual |
           +---- result: [{flight data}, ...] | function             |
                                              +----------------------+
```

- Note: the **LLM never touches real data directly**. It only sees: (a) the tool's name/description/schema and (b) the
  result after the host runs it.

### 5. Minimal example

Tool schema (a contract, not code):

```json
{
  "name": "search_flights",
  "description": "Search for available flights between two cities on a given date.",
  "parameters": {
    "type": "object",
    "properties": {
      "from": {
        "type": "string"
      },
      "to": {
        "type": "string"
      },
      "date": {
        "type": "string"
      }
    },
    "required": [
      "from",
      "to",
      "date"
    ]
  }
}
```

When the user says **"Find me a flight from Delhi to Goa next Friday."** the LLM emits:

```json
{
  "tool_call": "search_flights",
  "arguments": {
    "from": "Delhi",
    "to": "Goa",
    "date": "2026-09-25"
  }
}
```

The host then runs the actual `search_flights` function (stubbed) and returns a result, which the LLM uses to write the
final human-readable answer.

### 6. Professional articulation

> "Tool calling lets an LLM delegate real-world actions — like searching data or triggering a booking — to external
> functions, instead of trying to generate that information itself. The LLM only decides **which** tool to call and **with
what arguments**; a separate host process actually executes it and returns the result."

- **Jargon check:** *"Host process"* = the application that manages the conversation and has permission to actually run
  code (e.g., ChatGPT's backend, or a custom app you build).

### 7. Hands-on task

**Goal:** Simulate tool calling manually in Python — no MCP, no real LLM API call yet. You play the role of "host" and
hardcode what an LLM *would* request, then run the stub function yourself.

**File to create:** `tool_calling_demo.py`

```python
import json


# --- Stub function the LLM will request ---
def search_flights(from_city: str, to_city: str, date: str) -> list[dict]:
    """Pretend this hits a real flight search API. For now, it's mock data."""
    return [
        {
            "flight_id": "AI101",
            "from": from_city,
            "to": to_city,
            "date": date,
            "price_usd": 120,
        },
        {
            "flight_id": "6E202",
            "from": from_city,
            "to": to_city,
            "date": date,
            "price_usd": 95,
        },
    ]


# --- This JSON simulates what an LLM WOULD output when it decides to call a tool ---
simulated_llm_tool_call = {
    "tool_call": "search_flights",
    "arguments": {"from_city": "Delhi", "to_city": "Goa", "date": "2026-09-25"},
}


def run_tool_call(tool_call: dict):
    """This is the 'host' logic: read what tool the LLM wants, and actually run it."""
    name = tool_call["tool_call"]
    args = tool_call["arguments"]

    if name == "search_flights":
        result = search_flights(**args)
    else:
        raise ValueError(f"Unknown tool: {name}")

    return result


if __name__ == "__main__":
    print("LLM requested tool call:")
    print(json.dumps(simulated_llm_tool_call, indent=2))

    result = run_tool_call(simulated_llm_tool_call)

    print("\nHost executed the tool and got this structured result:")
    print(json.dumps(result, indent=2))
```

**Exact commands to run (same on Intel and Apple Silicon — pure Python, no native deps):**

```bash
python3 tool_calling_demo.py
```

**Result observed:** Printed output showed the mock/hardcoded data — confirming the host never touches real flight data;
it only runs whatever mock function was wired up. The LLM's "intelligence" is separate from the "execution."

---

## Concept 2: How a Real LLM Decides *When* to Emit a Tool Call

### 1. Plain-language definition

- In Concept 1, the tool call was **hardcoded** — we pretended the LLM already decided to call `search_flights`.
- In reality, when you call an LLM API (OpenAI, Anthropic, etc.), you send it:
    1. The user's message.
    2. A **list of available tools** (schemas, like the `search_flights` one from before).
- The LLM then **decides on its own**, based on the user's wording, whether to:
    - (a) answer directly with text, or
    - (b) emit a tool call request instead of text.
- This decision is called **intent interpretation** — the "LLM interprets intent" step in Flow 1.

### 2. Why it matters

- This is the actual "smart" part of the pipeline. The LLM must correctly:
    - Recognize **"find me a flight"** → intent = search flights (not hotels, not weather).
    - Extract structured arguments (`from`, `to`, `date`) from unstructured, messy human language ("next Friday" → an
      actual date).
- If this step is wrong, everything downstream (MCP tool call, structured content, widget) never fires, or fires with
  wrong data.
- This is **probabilistic**, not deterministic — the LLM might sometimes fail to call a tool when it should, or call the
  wrong one. Production systems must handle that (covered later under guardrails).

### 3. Building it from prerequisites

- Prerequisite: Concept 1 — tool calls are JSON requests the host executes.
- New idea: the LLM API itself has a **built-in feature** (not something you code) that:
    - Accepts a `tools` parameter (schemas) alongside your normal chat messages.
    - Returns either a normal text response, OR a special `"tool_calls"` field in its response object.
- You, as the host, just **check which one came back**.

### 4. Visual model

```
Request to LLM API:
  messages: [{ role: "user", content: "Find me a flight from Delhi to Goa next Friday" }]
  tools: [ search_flights schema, search_hotels schema ]
              |
              v
      +-----------------------------+
      | LLM API decides:            |
      | - intent = search_flights   |
      | - args = {Delhi, Goa, date} |
      +-----------------------------+
              |
              v
Response from LLM API:
  finish_reason: "tool_calls"
  tool_calls: [{ name: "search_flights", arguments: {...} }]
```

- Compare: if user said **"What's the capital of France?"** → same request, but response would be
  `finish_reason: "stop"` with plain text — **no tool call**, because no tool matches that intent.

### 5. Minimal example

Real OpenAI-style request/response shape (illustrative):

**You send:**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Find me a flight from Delhi to Goa next Friday"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_flights",
        "description": "Search for available flights between two cities on a given date.",
        "parameters": {
          "type": "object",
          "properties": {
            "from_city": {
              "type": "string"
            },
            "to_city": {
              "type": "string"
            },
            "date": {
              "type": "string",
              "description": "ISO 8601 date"
            }
          },
          "required": [
            "from_city",
            "to_city",
            "date"
          ]
        }
      }
    }
  ]
}
```

**LLM responds (simplified):**

```json
{
  "finish_reason": "tool_calls",
  "message": {
    "tool_calls": [
      {
        "id": "call_abc123",
        "function": {
          "name": "search_flights",
          "arguments": "{\"from_city\":\"Delhi\",\"to_city\":\"Goa\",\"date\":\"2026-09-25\"}"
        }
      }
    ]
  }
}
```

- Note: `arguments` comes back as a **JSON string**, not a JSON object — the host must `json.loads()` it.

### 6. Professional articulation

> "Intent interpretation happens inside the LLM call itself: given the user's message and a set of tool schemas, the
> model decides whether to respond in natural language or to emit a structured tool call with extracted arguments. As the
> host, we don't write logic to detect intent — we inspect the model's response to see if it chose to call a tool."

- **Jargon check:** *"finish_reason"* = a field the API returns telling you **why** the model stopped generating (e.g.,
  `"stop"` for a normal answer, `"tool_calls"` for a tool request).

### 7. Hands-on task

**Goal:** Make a **real** OpenAI API call, give it the `search_flights` tool schema, and observe the model deciding to
call it — no execution yet, just observe the decision.

You'll need an OpenAI API key. Set it as an environment variable so it's never hardcoded in the file.

**File to create:** `intent_demo.py`

```python
import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights between two cities on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string"},
                    "to_city": {"type": "string"},
                    "date": {
                        "type": "string",
                        "description": "ISO 8601 date, e.g. 2026-09-25"
                    },
                },
                "required": ["from_city", "to_city", "date"],
            },
        },
    }
]


def ask(user_message: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_message}],
        tools=tools,
    )
    choice = response.choices[0]
    print(f"\nUser said: {user_message!r}")
    print(f"finish_reason: {choice.finish_reason}")

    if choice.message.tool_calls:
        for tc in choice.message.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"Tool call requested: {tc.function.name}")
            print(f"Arguments: {json.dumps(args, indent=2)}")
    else:
        print(f"Direct answer: {choice.message.content}")


if __name__ == "__main__":
    ask("Find me a flight from Delhi to Goa on 2026-09-25")
    ask("What's the capital of France?")
```

**Exact commands to run (identical on Intel and Apple Silicon — pure Python + pip package, no native binaries):**

```bash
pip3 install openai
export OPENAI_API_KEY="your-api-key-here"
python3 intent_demo.py
```

**Prediction check:** For the first question, `finish_reason` should be `"tool_calls"` (the model recognizes the
flight-search intent and extracts arguments). For the second question (capital of France), `finish_reason` should be
`"stop"` with a plain-text answer, since no available tool matches that intent.

---

## Next Up: Concept 3

Why we need **MCP (Model Context Protocol)** at all - i.e., what problem MCP solves that plain tool-calling (as done 
above) does not.
