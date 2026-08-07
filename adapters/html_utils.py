import re


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def first_href(text: str) -> str | None:
    match = re.search(r'href="([^"]+)"', text)
    return match.group(1) if match else None


def apply_url_from_cell(cell: str) -> str | None:
    """Prefer direct application links over Simplify/company profile links."""
    urls = re.findall(r'href="([^"]+)"', cell)
    for url in urls:
        lower = url.lower()
        if "simplify.jobs/c/" in lower:
            continue
        if "simplify.jobs/p/" in lower:
            continue
        if "imgur.com" in lower:
            continue
        return url
    return urls[0] if urls else None
