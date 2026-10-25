import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["CONSENT_STATE_DIR"] = tempfile.mkdtemp(prefix="consent-phone-test-")
from consent_tokens import core, grant, guard  # noqa: E402


def call(session, cmd, tool="Bash"):
    return guard.decide({"session_id": session, "tool_name": tool, "tool_input": {"command": cmd}})


class PhoneGroupTests(unittest.TestCase):
    def setUp(self):
        core.write_state({})

    def test_device_commands_are_denied_even_read_only(self):
        for cmd in ("adb shell ls /sdcard", "adb pull /sdcard/a.txt .", "adb install app.apk", "adb -d shell id",
                    "adb exec-out screencap -p > s.png", "adb.exe -s R5XXXXXXXX shell", "scrcpy", "ideviceinstaller -l"):
            self.assertIsNotNone(call("a", cmd), cmd)

    def test_listing_and_server_commands_pass(self):
        for cmd in ("adb devices", "adb version", "adb start-server", "adb kill-server", "ls -la"):
            self.assertIsNone(call("a", cmd), cmd)

    def test_prose_that_mentions_adb_passes(self):
        self.assertIsNone(call("a", "echo notes about adb and phones"))

    def test_emulator_pinned_calls_pass_without_consent(self):
        self.assertIsNone(call("a", "adb -s emulator-5554 shell getprop ro.build.version.release"))
        self.assertIsNone(call("a", "adb.exe -s emulator-5556 install app.apk"))

    def test_one_pinned_call_does_not_cover_a_bare_one(self):
        self.assertIsNotNone(call("a", "adb -s emulator-5554 devices; adb shell ls"))
        self.assertIsNotNone(call("a", "adb -s emulator-5554 shell ls && adb pull /sdcard/x ."))
        self.assertIsNotNone(call("a", "adb -s emulator-5554 shell ls\nadb shell id"))

    def test_serial_text_inside_another_call_is_not_a_pin(self):
        self.assertIsNotNone(call("a", "adb shell echo -s emulator-5554"))

    def test_a_real_device_serial_is_not_exempt(self):
        self.assertIsNotNone(call("a", "adb -s 1234ABCD shell id"))

    def test_typed_phrase_opens_phone_only(self):
        grant.handle({"session_id": "a", "prompt": "allow phone"})
        self.assertIsNone(call("a", "adb shell ls"))
        self.assertIsNotNone(call("a", "curl https://x.example/checkout"))
        self.assertIsNotNone(call("b", "adb shell ls"))

    def test_revoke_closes_it(self):
        grant.handle({"session_id": "a", "prompt": "allow phone"})
        grant.handle({"session_id": "a", "prompt": "revoke consent"})
        self.assertIsNotNone(call("a", "adb shell ls"))

    def test_model_text_cannot_grant(self):
        self.assertIsNone(grant.handle({"session_id": "a", "prompt": "never allow phone"}))
        self.assertIsNotNone(call("a", "adb shell ls"))

    def test_other_tools_are_not_checked(self):
        self.assertIsNone(guard.decide({"session_id": "a", "tool_name": "Read", "tool_input": {"file_path": "docs/adb shell.md"}}))

    def test_denial_names_the_phrase(self):
        out = call("a", "adb shell ls")
        self.assertIn("allow phone", out["hookSpecificOutput"]["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
