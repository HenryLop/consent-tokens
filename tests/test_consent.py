import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["CONSENT_STATE_DIR"] = tempfile.mkdtemp(prefix="consent-test-")
from consent_tokens import core, grant, guard  # noqa: E402

PAY = "open https://x.example/checkout"
API = "curl https://api.openai.com/v1/chat"


def call(session, cmd, tool="Bash"):
    return guard.decide({"session_id": session, "tool_name": tool, "tool_input": {"command": cmd}})


class ConsentTests(unittest.TestCase):
    def setUp(self):
        core.write_state({})

    def test_default_deny(self):
        self.assertIsNotNone(call("a", PAY))
        self.assertIsNotNone(call("a", API))

    def test_reads_pass(self):
        self.assertIsNone(call("a", "curl https://shop.example.com/pricing"))
        self.assertIsNone(call("a", "ls -la"))

    def test_typed_phrase_opens_one_group_only(self):
        grant.handle({"session_id": "a", "prompt": "allow pay"})
        self.assertIsNone(call("a", PAY))
        self.assertIsNotNone(call("a", API))

    def test_session_scoped(self):
        grant.handle({"session_id": "a", "prompt": "allow pay"})
        self.assertIsNotNone(call("b", PAY))

    def test_expires(self):
        core.grant("a", ["pay"], now=time.time() - 31 * 60)
        self.assertIsNotNone(call("a", PAY))

    def test_negated_or_quoted_does_not_grant(self):
        for p in ("I will never say allow pay", 'the phrase "allow pay" opens it', "don't allow pay"):
            self.assertIsNone(grant.handle({"session_id": "a", "prompt": p}), p)
        self.assertIsNotNone(call("a", PAY))

    def test_revoke(self):
        grant.handle({"session_id": "a", "prompt": "allow all"})
        self.assertIsNone(call("a", PAY))
        grant.handle({"session_id": "a", "prompt": "revoke consent"})
        self.assertIsNotNone(call("a", PAY))

    def test_grants_add_up(self):
        grant.handle({"session_id": "a", "prompt": "allow pay"})
        grant.handle({"session_id": "a", "prompt": "allow api"})
        self.assertIsNone(call("a", API))
        self.assertIsNone(call("a", PAY))

    def test_tool_scope(self):
        self.assertIsNone(guard.decide({"session_id": "a", "tool_name": "Read",
                                        "tool_input": {"file_path": "notes/billing/readme.md"}}))


if __name__ == "__main__":
    unittest.main()
