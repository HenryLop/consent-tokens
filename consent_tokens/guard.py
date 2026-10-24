"""PreToolUse hook: deny a tool call that touches a closed consent group."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from consent_tokens import core  # noqa: E402


def decide(event):
    hit = core.find_violation(event.get("tool_name", ""), event.get("tool_input"), event.get("session_id", ""))
    if not hit:
        return None
    group, matched = hit
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "BLOCKED: group '%s' is closed (matched: %s). Prepare everything, but do not "
            "perform this action. Only the user can open it, by typing '%s %s' in the chat "
            "(%d minutes, this session only). You cannot grant it yourself."
            % (group, matched, core.KEYWORD, group, core.MINUTES))}}


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    out = decide(event)
    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    main()
