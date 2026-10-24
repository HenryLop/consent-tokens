"""UserPromptSubmit hook: a phrase typed by the user opens a group for a short time.

Only user prompts reach this hook, never model output, which is what makes the
phrase a token the agent cannot mint for itself.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from consent_tokens import core  # noqa: E402


def handle(event):
    prompt, session = event.get("prompt") or "", event.get("session_id", "")
    if core.wants_revoke(prompt):
        core.revoke(session)
        return "Consent closed. Every risky group is denied again."
    groups = core.parse_grant(prompt, set(core.load_groups()))
    if not groups:
        return None
    g = core.grant(session, groups)
    return ("The user opened consent for: %s. Valid %d minutes, this session only. "
            "Still state what the action is, to whom and how much before the final click."
            % (", ".join(g["groups"]), core.MINUTES))


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    msg = handle(event)
    if msg:
        print(msg)


if __name__ == "__main__":
    main()
