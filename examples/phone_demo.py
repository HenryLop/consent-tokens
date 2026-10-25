"""Example group: a phone behind a debug bridge. Every device command is denied until the user types a phrase.

    python examples/phone_demo.py

No phone, adb or emulator is needed; the commands are only checked, never run.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["CONSENT_STATE_DIR"] = tempfile.mkdtemp(prefix="consent-phone-demo-")


def hook(script, event):
    p = subprocess.run([sys.executable, os.path.join(ROOT, "consent_tokens", script)],
                       input=json.dumps(event), capture_output=True, text=True)
    return p.stdout.strip()


def check(session, cmd):
    out = hook("guard.py", {"session_id": session, "tool_name": "Bash", "tool_input": {"command": cmd}})
    return "DENIED " if "deny" in out else "allowed"


def row(label, session, cmd):
    print("%-44s %s  %s" % (label, check(session, cmd), cmd))


row("1. list attached devices", "s1", "adb devices")
row("2. read-only: list files on the phone", "s1", "adb shell ls /sdcard")
row("3. read-only: screenshot", "s1", "adb exec-out screencap -p > shot.png")
row("4. install an app", "s1", "adb install app.apk")
row("5. same, pinned to an emulator", "s1", "adb -s emulator-5554 install app.apk")
row("6. pinned call hiding a bare one", "s1", "adb -s emulator-5554 devices; adb shell id")
print("   user types: allow phone ->", hook("grant.py", {"session_id": "s1", "prompt": "ok, allow phone"})[:48] + "...")
row("7. read-only again, same session", "s1", "adb shell ls /sdcard")
row("8. read-only, another session", "s2", "adb shell ls /sdcard")
print("   user types: revoke consent ->", hook("grant.py", {"session_id": "s1", "prompt": "revoke consent"})[:34] + "...")
row("9. read-only after revoke", "s1", "adb shell ls /sdcard")
