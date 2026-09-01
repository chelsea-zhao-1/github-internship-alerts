import hashlib
import re


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _url_key(role: dict) -> str | None:
    url = (role.get("url") or "").strip()
    if not url:
        return None
    clean = url.split("?")[0].rstrip("/").lower()
    return f"url:{clean}"


def _identity_key(role: dict) -> str:
    company = _normalize(role.get("company") or "")
    company = re.sub(r"\s*\([^)]*\)\s*", " ", company)
    company = re.sub(r"\b(?:inc|llc|ltd|corp|co)\.?\s*$", "", company).strip()
    title = _normalize(role.get("title") or "")
    location = _normalize(role.get("location") or "")
    location = re.sub(r"\s*\+\d+\s*$", "", location)
    location = re.sub(
        r",?\s*(?:united states|usa|u\.s\.a\.?|u\.s\.?)\s*$",
        "",
        location,
        flags=re.I,
    )
    location = re.sub(r"^remote\s*[-–—:]?\s*", "", location)
    location = location.strip(" ,")
    composite = "|".join((company, title, location))
    digest = hashlib.sha256(composite.encode()).hexdigest()[:20]
    return f"id:{digest}"


def role_keys(role: dict) -> list[str]:
    """
    IDs used to treat one listing as the same role across GitHubs and days.
    URL match and company+title+location match both count as the same role.
    """
    keys = []
    url = _url_key(role)
    if url:
        keys.append(url)
    keys.append(_identity_key(role))
    return keys


def role_key(role: dict) -> str:
    """Primary ID (URL if present, otherwise company + title + location)."""
    return role_keys(role)[0]


def dedupe_roles(roles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []

    for role in roles:
        keys = role_keys(role)
        if any(key in seen for key in keys):
            continue
        seen.update(keys)
        unique.append(role)

    return unique
