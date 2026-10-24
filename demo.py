"""One-command demo: deny -> typed phrase -> allow -> other session still denied -> revoke -> deny.

    python demo.py
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ["CONSENT_STATE_DIR"] = tempfile.mkdtemp(prefix="consent-demo-")
PAY_URL = "shop.example.com/checkout"


def hook(script, event):
    p = subprocess.run([sys.executable, os.path.join(ROOT, "consent_tokens", script)],
                       input=json.dumps(event), capture_output=True, text=True)
    return p.stdout.strip()


def tool(session, url):
    out = hook("guard.py", {"session_id": session, "tool_name": "Bash",
                            "tool_input": {"command": "curl https://%s" % url}})
    return "DENIED" if "deny" in out else "allowed"


def say(label, value):
    print("%-52s %s" % (label, value))


say("1. agent opens a payment page", tool("s1", PAY_URL))
say("2. agent opens a normal page", tool("s1", "shop.example.com/products"))
say("3. user types 'allow pay' in session s1", hook("grant.py", {"session_id": "s1", "prompt": "ok, allow pay"})[:34] + "...")
say("4. agent opens the payment page again (s1)", tool("s1", PAY_URL))
say("5. same action in another session (s2)", tool("s2", PAY_URL))
say("6. user types 'revoke consent' in s1", hook("grant.py", {"session_id": "s1", "prompt": "revoke consent"})[:34] + "...")
say("7. agent tries the payment page again (s1)", tool("s1", PAY_URL))
say("8. 'never say allow pay' must open nothing", hook("grant.py", {"session_id": "s1", "prompt": "never say allow pay"}) or "(nothing opened)")
