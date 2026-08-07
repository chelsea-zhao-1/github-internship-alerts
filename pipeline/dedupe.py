import hashlib
import re


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def role_key(role: dict) -> str:
    """
    Stable ID for deduplication across overlapping GitHub repos.
    Prefer application URL; fall back to company + title + location.
    """
    url = (role.get("url") or "").strip()
    if url:
        clean = url.split("?")[0].rstrip("/").lower()
        return f"url:{clean}"

    composite = "|".join(
        _normalize(role.get(field, "") or "")
        for field in ("company", "title", "location")
    )
    digest = hashlib.sha256(composite.encode()).hexdigest()[:20]
    return f"hash:{digest}"


def dedupe_roles(roles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []

    for role in roles:
        key = role_key(role)
        if key in seen:
            continue
        seen.add(key)
        unique.append(role)

    return unique
