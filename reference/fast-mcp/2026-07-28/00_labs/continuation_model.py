"""A domain state-machine simulation, NOT an MCP or OAuth implementation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    owner: str
    ticket: str
    phase: str = "needs_approval"


class DemoService:
    def __init__(self):
        self.intents = {"op-1": Intent("alice", "T-100")}
        self.results = {}
        self.writes = 0

    def approve(self, operation: str, caller: str, action: str, approved: bool):
        intent = self.intents[operation]
        if caller != intent.owner:
            raise PermissionError("Operation belongs to another user")
        if operation in self.results:
            return self.results[operation]
        if action != "accept" or approved is not True:
            return {"status": "not_applied"}
        self.writes += 1
        result = {"status": "closed", "ticket": intent.ticket}
        self.results[operation] = result
        return result


if __name__ == "__main__":
    service = DemoService()
    assert service.approve("op-1", "alice", "accept", False)["status"] == "not_applied"
    assert service.writes == 0
    try:
        service.approve("op-1", "bob", "accept", True)
    except PermissionError:
        pass
    else:
        raise AssertionError("Cross-user operation accepted")
    first = service.approve("op-1", "alice", "accept", True)
    replay = service.approve("op-1", "alice", "accept", True)
    assert first == replay and service.writes == 1
    print("Decline, identity isolation, and sequential replay checks passed")
