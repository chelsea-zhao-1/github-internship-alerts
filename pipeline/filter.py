import re

# Internships always pass (unless they look like SWE I/II).
INTERN_RE = re.compile(
    r"\b(?:intern(?:ship)?s?|co-?ops?|summer\s+associates?)\b",
    re.I,
)

# Non-intern titles that are still early-pipeline.
ALLOW_RE = re.compile(
    r"\b(?:analysts?|early[-\s]?career|students?|apprentices?|rotationals?)\b",
    re.I,
)

# SWE I / SWE 1 / Software Engineer II / Engineer I/II — not "Intern".
LEVEL_RE = re.compile(
    r"""
    \b(?:
        swe|sde|
        software\s+(?:development\s+)?engineer|
        software\s+dev(?:eloper)?|
        (?:front-?end|back-?end|full-?stack)?\s*engineer
    )
    \s*[-/]?\s*
    (?:i{1,3}|[123])
    (?:\s*/\s*(?:i{1,3}|[123]))?
    \b
    """,
    re.I | re.X,
)

EXPERIENCE_RE = re.compile(
    r"""
    \b(?:
        \d+\s*[-–—]\s*\d+\s*\+?\s*years? |
        \d+\s*\+\s*years? |
        \d+\s*years?\s+(?:of\s+)?(?:e/?xperience|exp)
    )\b
    |
    \b(?:master'?s?|m\.s\.|phd|ph\.d)\b
    """,
    re.I | re.X,
)

SENIOR_RE = re.compile(
    r"\b(?:senior|staff|principal|sr\.?|experienced|level\s*[2-9])\b",
    re.I,
)


def is_relevant_role(role: dict) -> bool:
    """Keep intern / analyst / early-career titles; drop SWE I/II and experienced roles."""
    title = role.get("title") or ""
    if LEVEL_RE.search(title):
        return False
    if INTERN_RE.search(title):
        return True
    if EXPERIENCE_RE.search(title) or SENIOR_RE.search(title):
        return False
    return bool(ALLOW_RE.search(title))


def filter_roles(roles: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    dropped: list[dict] = []
    for role in roles:
        (kept if is_relevant_role(role) else dropped).append(role)
    return kept, dropped
