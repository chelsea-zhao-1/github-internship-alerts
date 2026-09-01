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

# Comma before the abbrev so "IN" / "OR" do not match English words.
_US_STATE_ABBREV = (
    r"AL|AK|AZ|AR|CA|CO|CT|DC|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|"
    r"MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|"
    r"UT|VT|VA|WA|WV|WI|WY"
)
US_ABBREV_RE = re.compile(rf",\s*(?:{_US_STATE_ABBREV})\b", re.I)

US_STATE_NAME_RE = re.compile(
    r"\b(?:alabama|alaska|arizona|arkansas|california|colorado|connecticut|"
    r"delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|"
    r"kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
    r"mississippi|missouri|montana|nebraska|nevada|new\s+hampshire|"
    r"new\s+jersey|new\s+mexico|new\s+york|north\s+carolina|north\s+dakota|"
    r"ohio|oklahoma|oregon|pennsylvania|rhode\s+island|south\s+carolina|"
    r"south\s+dakota|tennessee|texas|utah|vermont|virginia|washington|"
    r"west\s+virginia|wisconsin|wyoming|district\s+of\s+columbia)\b",
    re.I,
)

US_COUNTRY_RE = re.compile(
    r"\b(?:usa|u\.s\.a\.?|united\s+states)\b|🇺🇸|(?:^|[\s\-])US(?:-|\b)",
    re.I,
)

US_CITY_TOKEN_RE = re.compile(r"nyc|\bsfo?\b", re.I)

FOREIGN_RE = re.compile(
    r"""
    \b(?:
        canada|mexico|brazil|argentina|chile|colombia|
        united\s+kingdom|\buk\b|england|scotland|wales|ireland|
        germany|france|italy|spain|portugal|netherlands|belgium|
        switzerland|sweden|norway|denmark|finland|poland|austria|
        czech|greece|turkey|russia|ukraine|
        india|china|japan|korea|singapore|malaysia|indonesia|
        thailand|vietnam|philippines|taiwan|hong\s+kong|
        australia|new\s+zealand|israel|
        uae|united\s+arab\s+emirates|dubai|saudi|qatar|
        egypt|south\s+africa|nigeria|kenya|
        europe|emea|apac|latam|worldwide
    )\b
    |
    🇨🇦|🇬🇧|🇮🇳|🇨🇳|🇩🇪|🇫🇷|🇯🇵|🇦🇺|🇸🇬|🇮🇪|🇳🇱|🇸🇪|🇨🇭|🇧🇷|🇲🇽|🇰🇷|🇦🇪|🇮🇹
    """,
    re.I | re.X,
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


def is_us_location(location: str) -> bool:
    """Keep US (and mixed US + elsewhere) locations; drop foreign-only."""
    text = (location or "").strip()
    if not text:
        return True
    if (
        US_COUNTRY_RE.search(text)
        or US_ABBREV_RE.search(text)
        or US_STATE_NAME_RE.search(text)
        or US_CITY_TOKEN_RE.search(text)
    ):
        return True
    if FOREIGN_RE.search(text):
        return False
    return True


def filter_roles(roles: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    dropped: list[dict] = []
    for role in roles:
        keep = is_relevant_role(role) and is_us_location(role.get("location") or "")
        (kept if keep else dropped).append(role)
    return kept, dropped
