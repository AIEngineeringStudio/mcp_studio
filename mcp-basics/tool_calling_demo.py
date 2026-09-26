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