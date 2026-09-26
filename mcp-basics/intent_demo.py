import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
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