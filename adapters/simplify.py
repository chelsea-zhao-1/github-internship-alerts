import re

from adapters.html_utils import apply_url_from_cell, strip_html


def _extract_tables(content: str) -> list[tuple[str, str]]:
    tables: list[tuple[str, str]] = []
    current_section = "General"

    parts = re.split(r"(<table>.*?</table>)", content, flags=re.DOTALL | re.IGNORECASE)
    for part in parts:
        if part.lower().startswith("<table>"):
            tables.append((current_section, part))
            continue

        for match in re.finditer(r"^## (.+)$", part, flags=re.MULTILINE):
            current_section = match.group(1).strip()

    return tables


def _parse_row(row_html: str) -> list[str] | None:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL | re.IGNORECASE)
    if not cells:
        return None
    return [cell.strip() for cell in cells]


def _normalize_company(cell: str) -> str:
    text = strip_html(cell)
    if text == "?":
        return ""
    return text


def parse_simplify(content: str) -> list[dict]:
    roles: list[dict] = []
    last_company = ""

    for section, table_html in _extract_tables(content):
        row_htmls = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.DOTALL | re.IGNORECASE)

        for row_html in row_htmls:
            cells = _parse_row(f"<tr>{row_html}</tr>")
            if not cells or len(cells) < 4:
                continue
            if strip_html(cells[0]).lower() == "company":
                continue

            company = _normalize_company(cells[0])
            if company:
                last_company = company
            elif last_company:
                company = last_company
            else:
                continue

            title = strip_html(cells[1])
            location = strip_html(cells[2])
            age = strip_html(cells[4]) if len(cells) > 4 else ""

            if not title:
                continue

            url = apply_url_from_cell(cells[3]) or ""

            roles.append({
                "company": company,
                "title": title,
                "location": location,
                "url": url,
                "age": age,
                "section": section,
            })

    return roles
