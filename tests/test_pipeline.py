"""Tests - no network, no Gmail."""

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.dedupe import dedupe_roles, role_key


SPEEDYAPPLY_SAMPLE = """
### FAANG+

| Company | Position | Location | Salary | Posting | Age |
|---|---|---|---|---|---|
| Roblox | 2027 Software Engineer - Early Career | San Mateo, CA | $150k/yr | | 1d |

### Quant

| Company | Position | Location | Salary | Posting | Age |
|---|---|---|---|---|---|
| Citadel | Software Engineer - University Graduate | Houston, TX | $338k/yr | | 23d |

### Other

| Company | Position | Location | Posting | Age |
|---|---|---|---|---|
| <a href="https://www.getclera.com/"><strong>Clera</strong></a> | Embedded Software Engineer | Austin, TX | <a href="https://jobs.ashbyhq.com/clera/f523d3fa"><img src="x.png"/></a> | 0d |
"""

SIMPLIFY_SAMPLE = """
## Software Engineering Internship Roles

<table>
<thead>
<tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Age</th></tr>
</thead>
<tbody>
<tr>
<td><strong><a href="https://simplify.jobs/c/TikTok">TikTok</a></strong></td>
<td>Software Engineer Intern</td>
<td>Seattle, WA</td>
<td><a href="https://lifeattiktok.com/search/123?utm_source=Simplify">Apply</a></td>
<td>0d</td>
</tr>
<tr>
<td>?</td>
<td>Backend Intern</td>
<td>San Jose, CA</td>
<td><a href="https://lifeattiktok.com/search/456?utm_source=Simplify">Apply</a></td>
<td>1d</td>
</tr>
</tbody>
</table>
"""


class TestSpeedyApplyParser:
    def test_parses_requested_sections_only(self):
        from adapters.speedyapply import parse_speedyapply

        roles = parse_speedyapply(SPEEDYAPPLY_SAMPLE, ["FAANG+", "Other"])
        companies = {r["company"] for r in roles}
        assert "Roblox" in companies
        assert "Clera" in companies
        assert "Citadel" not in companies

    def test_extracts_apply_url(self):
        from adapters.speedyapply import parse_speedyapply

        roles = parse_speedyapply(SPEEDYAPPLY_SAMPLE, ["Other"])
        clera = next(r for r in roles if r["company"] == "Clera")
        assert "ashbyhq.com" in clera["url"]


class TestSimplifyParser:
    def test_parses_html_table(self):
        from adapters.simplify import parse_simplify

        roles = parse_simplify(SIMPLIFY_SAMPLE)
        assert len(roles) == 2
        assert roles[0]["company"] == "TikTok"
        assert roles[1]["company"] == "TikTok"
        assert roles[1]["title"] == "Backend Intern"

    def test_prefers_direct_apply_url(self):
        from adapters.simplify import parse_simplify

        roles = parse_simplify(SIMPLIFY_SAMPLE)
        assert roles[0]["url"].startswith("https://lifeattiktok.com/")


class TestDedupe:
    def test_same_url_deduped(self):
        role_a = {
            "company": "TikTok",
            "title": "SWE Intern",
            "location": "Seattle, WA",
            "url": "https://example.com/job/1?utm_source=x",
        }
        role_b = {**role_a, "company": "TikTok (Simplify)"}
        result = dedupe_roles([role_a, role_b])
        assert len(result) == 1

    def test_different_roles_kept(self):
        roles = [
            {"company": "A", "title": "Intern", "location": "NY", "url": ""},
            {"company": "B", "title": "Intern", "location": "NY", "url": ""},
        ]
        assert len(dedupe_roles(roles)) == 2


class TestState:
    def test_cold_start_when_missing(self, tmp_path, monkeypatch):
        from pipeline import state as state_mod

        monkeypatch.chdir(tmp_path)
        loaded, cold = state_mod.load_state()
        assert cold is True
        assert loaded["roles"] == {}

    def test_compute_new_roles(self):
        from pipeline.state import compute_new_roles

        current = [
            {"company": "A", "title": "Intern", "location": "NY", "url": "https://x.com/1"},
        ]
        seen = {}
        new = compute_new_roles(current, seen, role_key)
        assert len(new) == 1

        seen = {role_key(current[0]): {}}
        new = compute_new_roles(current, seen, role_key)
        assert new == []


class TestMainColdStart:
    @patch("main.send_email")
    @patch("main._fetch_source_roles")
    def test_init_email_on_cold_start(self, mock_fetch, mock_send, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "sources.yaml").write_text(
            "sources:\n"
            "  - name: test\n"
            "    display_name: Test\n"
            "    type: simplify\n"
            "    repo: org/repo\n"
            "    path: README.md\n"
        )
        monkeypatch.setenv("NOTIFY_EMAIL", "test@example.com")
        mock_fetch.return_value = [
            {"company": "Co", "title": "Intern", "location": "NY", "url": "https://x.com/1", "source": "Test"},
        ]

        from main import main

        assert main() == 0
        mock_send.assert_called_once()
        subject, _ = mock_send.call_args[0]
        assert "initialized" in subject.lower()
        seen = json.loads((tmp_path / "seen.json").read_text())
        assert len(seen["roles"]) == 1
