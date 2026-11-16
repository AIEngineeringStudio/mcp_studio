"""Domain checks do not require an LLM or a network service."""
import unittest
from server import lookup_ticket


class TicketTests(unittest.TestCase):
    def test_existing_ticket(self):
        self.assertEqual(lookup_ticket("T-100")["status"], "open")

    def test_unknown_ticket(self):
        with self.assertRaisesRegex(ValueError, "Unknown ticket"):
            lookup_ticket("missing")

    def test_caller_cannot_mutate_repository_record(self):
        result = lookup_ticket("T-100")
        result["status"] = "closed"
        self.assertEqual(lookup_ticket("T-100")["status"], "open")


if __name__ == "__main__":
    unittest.main()
