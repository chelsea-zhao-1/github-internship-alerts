import re

from adapters.html_utils import apply_url_from_cell, first_href, strip_html


def _split_sections(content: str) -> dict[str, str]:
    """Split markdown by ### headings into {heading: body}."""
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []

    for line in content.splitlines():
        heading = re.match(r"^### (.+)$", line.strip())
        if heading:
            if current is not None:
                sections[current] = "\n".join(lines)
            current = heading.group(1).strip()
            lines = []
        elif current is not None:
            lines.append(line)

    if current is not None:
        sections[current] = "\n".join(lines)

    return sections


def _parse_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or stripped.startswith("|---"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if cells and cells[0].lower() == "company":
        return None
    return cells


def _row_to_role(cells: list[str], section: str) -> dict | None:
    if len(cells) < 4:
        return None

    company_cell = cells[0]
    title = strip_html(cells[1])
    location = strip_html(cells[2])

    if not title or title in {"?", "Company", "Position"}:
        return None

    company = strip_html(company_cell) or company_cell
    if company in {"?", ""}:
        return None

    # FAANG+/Quant: Company | Position | Location | Salary | Posting | Age
    # Other:        Company | Position | Location | Posting | Age
    posting_idx = 4 if len(cells) >= 6 else 3
    age_idx = posting_idx + 1

    posting_cell = cells[posting_idx] if posting_idx < len(cells) else ""
    age = strip_html(cells[age_idx]) if age_idx < len(cells) else ""

    url = apply_url_from_cell(posting_cell) or first_href(company_cell)

    return {
        "company": company,
        "title": title,
        "location": location,
        "url": url or "",
        "age": age,
        "section": section,
    }


def parse_speedyapply(content: str, sections: list[str]) -> list[dict]:
    roles: list[dict] = []
    by_section = _split_sections(content)

    for section_name in sections:
        body = by_section.get(section_name, "")
        for line in body.splitlines():
            cells = _parse_table_row(line)
            if not cells:
                continue
            role = _row_to_role(cells, section_name)
            if role:
                roles.append(role)

    return roles
