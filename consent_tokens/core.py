"""Shared logic: group config, grant state, phrase parsing, tool matching.

State is one JSON file. A grant is keyed by session_id, so a grant typed in one
session never opens anything in another, and an agent cannot write a user prompt.
"""
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MINUTES = int(os.environ.get("CONSENT_MINUTES", "30"))
KEYWORD = os.environ.get("CONSENT_KEYWORD", "allow")


def state_path():
    d = os.environ.get("CONSENT_STATE_DIR") or os.path.join(os.path.expanduser("~"), ".consent-tokens")
    return os.path.join(d, "grants.json")


def load_groups():
    path = os.environ.get("CONSENT_GROUPS") or os.path.join(HERE, "groups.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_state():
    try:
        with open(state_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_state(state):
    path = state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh)


def is_open(session, group, now=None):
    now = time.time() if now is None else now
    g = read_state().get(session)
    if not g or g.get("until", 0) <= now:
        return False
    return "all" in g["groups"] or group in g["groups"]


# --- phrase parsing --------------------------------------------------------
NEGATED = re.compile(r"\b(no|never|don'?t|without|not)\b[^.;!?]{0,40}$", re.I)


def _negated_or_quoted(prompt, start):
    before = prompt[max(0, start - 60):start]
    return bool(NEGATED.search(before)) or before.rstrip().endswith(('"', "'", "`", "“"))


def parse_grant(prompt, known_groups):
    """Return the list of group names a typed prompt opens (may be empty)."""
    pat = re.compile(r"\b%s\s+([a-z]+)" % re.escape(KEYWORD), re.I)
    out = []
    for m in pat.finditer(prompt):
        word = m.group(1).lower()
        if (word in known_groups or word == "all") and not _negated_or_quoted(prompt, m.start()):
            out.append(word)
    return out


def wants_revoke(prompt):
    return bool(re.search(r"\b(revoke|close|clear)\s+(all\s+)?(consent|permissions?|grants?)\b", prompt, re.I))


def grant(session, groups, now=None):
    now = time.time() if now is None else now
    state = read_state()
    old = state.get(session)
    merged = set(groups)
    if old and old.get("until", 0) > now:
        merged |= set(old["groups"])
    state[session] = {"groups": sorted(merged), "until": now + MINUTES * 60}
    write_state(state)
    return state[session]


def revoke(session):
    state = read_state()
    state.pop(session, None)
    write_state(state)


# --- tool matching ---------------------------------------------------------
def find_violation(tool, tool_input, session):
    """Return (group, matched_text) for the first closed group the call touches."""
    text = json.dumps(tool_input or {}, ensure_ascii=False)
    for name, cfg in load_groups().items():
        if not any(re.fullmatch(t, tool) for t in cfg.get("tools", [".*"])):
            continue
        for p in cfg["patterns"]:
            m = re.search(p, text, re.I)
            if m and not is_open(session, name):
                return name, m.group(0)
    return None
