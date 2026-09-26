SEARCH_FLIGHTS_TOOL = {
    "type": "function",
    "name": "search_flights",
    "description": "Search for flights between two cities on a specific date.",
    "parameters": {
        "type": "object",
        "properties": {
            "from_city": {"type": "string"},
            "to_city": {"type": "string"},
            "date": {"type": "string"},
        },
        "required": ["from_city", "to_city", "date"],
        "additionalProperties": False,
    },
    "strict": True,
}


def validate_arguments(arguments: dict) -> list[str]:
    """
    Tiny teaching validator.

    This checks only the JSON Schema features used in this lesson.
    It is not a complete JSON Schema implementation.
    """
    parameters = SEARCH_FLIGHTS_TOOL["parameters"]
    properties = parameters["properties"]
    errors = []

    for required_name in parameters["required"]:
        if required_name not in arguments:
            errors.append(f"Missing required argument: {required_name}")

    if parameters["additionalProperties"] is False:
        for supplied_name in arguments:
            if supplied_name not in properties:
                errors.append(f"Unexpected argument: {supplied_name}")

    for name, value in arguments.items():
        if name in properties:
            expected_type = properties[name]["type"]

            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"{name} must be a string")

    return errors


candidate_calls = [
    {
        "label": "valid",
        "arguments": {
            "from_city": "Delhi",
            "to_city": "Goa",
            "date": "2026-09-25",
        },
    },
    {
        "label": "missing date",
        "arguments": {
            "from_city": "Delhi",
            "to_city": "Goa",
        },
    },
    {
        "label": "unexpected argument",
        "arguments": {
            "from_city": "Delhi",
            "to_city": "Goa",
            "date": "2026-09-25",
            "delete_database": True,
        },
    },
    {
        "label": "wrong type",
        "arguments": {
            "from_city": "Delhi",
            "to_city": "Goa",
            "date": 20260925,
        },
    },
]


for candidate in candidate_calls:
    errors = validate_arguments(candidate["arguments"])

    if errors:
        print(f"{candidate['label']}: REJECTED")
        for error in errors:
            print(f"  - {error}")
    else:
        print(f"{candidate['label']}: ACCEPTED")