import json
import os
from datetime import datetime, timezone

SEEN_FILE = "seen.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_state() -> dict:
    return {
        "initialized_at": None,
        "last_checked": None,
        "last_status": None,
        "roles": {},
    }


def load_state() -> tuple[dict, bool]:
    if not os.path.exists(SEEN_FILE):
        return _empty_state(), True

    try:
        with open(SEEN_FILE) as f:
            state = json.load(f)
        if not isinstance(state, dict) or "roles" not in state:
            raise ValueError("Unexpected state shape")
        return state, False
    except Exception as exc:
        print(f"[state] Warning: could not parse {SEEN_FILE} ({exc}). Treating as cold start.")
        return _empty_state(), True


def save_state(state: dict) -> None:
    state["last_checked"] = _now_iso()
    with open(SEEN_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def _keys(role: dict, key_fn) -> list[str]:
    result = key_fn(role)
    if isinstance(result, str):
        return [result]
    return list(result)


def compute_new_roles(current: list[dict], seen_roles: dict, key_fn) -> list[dict]:
    seen_ids = set(seen_roles.keys())
    for stored in seen_roles.values():
        if isinstance(stored, dict):
            seen_ids.update(_keys(stored, key_fn))
    new: list[dict] = []
    for role in current:
        if any(key in seen_ids for key in _keys(role, key_fn)):
            continue
        new.append(role)
    return new


def build_snapshot(roles: list[dict], existing: dict, key_fn, timestamp: str) -> dict:
    snapshot = dict(existing)
    for role in roles:
        ids = _keys(role, key_fn)
        first_seen = timestamp
        for rid in ids:
            prev = existing.get(rid)
            if prev and prev.get("first_seen"):
                first_seen = prev["first_seen"]
                break
        entry = {
            "company": role["company"],
            "title": role["title"],
            "location": role["location"],
            "url": role.get("url", ""),
            "section": role.get("section", ""),
            "source": role.get("source", ""),
            "first_seen": first_seen,
        }
        for rid in ids:
            snapshot[rid] = entry
    return snapshot
