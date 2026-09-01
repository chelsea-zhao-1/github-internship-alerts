"""Tests - no network, no Gmail."""

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.dedupe import dedupe_roles, role_key, role_keys
from pipeline.filter import is_us_location, filter_roles


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


class TestTitleFilter:
    def _ok(self, title: str) -> bool:
        from pipeline.filter import is_relevant_role

        return is_relevant_role({"title": title})

    def test_keeps_intern_analyst_early_career(self):
        assert self._ok("Software Engineer Intern - Summer 2027")
        assert self._ok("Data Analyst Intern")
        assert self._ok("Software Engineer - Early Career")
        assert self._ok("Data Analyst - Dashboard Developer")
        assert self._ok("Co-op Software Engineer")
        assert self._ok("Capital Markets Quant Summer Associate")

    def test_drops_swe_levels_even_with_early_career(self):
        assert not self._ok("Software Engineer I")
        assert not self._ok("Software Engineer II - Backend")
        assert not self._ok("SWE I - New Grad")
        assert not self._ok("Software Development Engineer I - Early Career")
        assert not self._ok("Front-End Engineer II")

    def test_drops_new_grad_and_experienced(self):
        assert not self._ok("Software Engineer Graduate - 2027 Start")
        assert not self._ok("New College Grad Software Engineer")
        assert not self._ok("Software Engineer - 1-2 years experience")
        assert not self._ok("Software Engineer - Master's Required")
        assert not self._ok("Senior Software Engineer")
        assert not self._ok("Experienced Front-End Insurance Analyst")
        assert not self._ok("Software Configuration Management Analyst - Level 2 or 3")

    def test_intern_not_confused_with_engineer_i(self):
        assert self._ok("Software Engineer Intern")
        assert self._ok("Software Engineer Intern - ML Infra - PhD")


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

    def test_same_identity_different_urls_deduped(self):
        role_a = {
            "company": "Google",
            "title": "Software Engineer Intern",
            "location": "Mountain View, CA, USA",
            "url": "https://speedyapply.example/google-1",
        }
        role_b = {
            "company": "Google",
            "title": "Software Engineer Intern",
            "location": "Mountain View, CA",
            "url": "https://simplify.example/google-1?utm_source=Simplify",
        }
        assert len(dedupe_roles([role_a, role_b])) == 1


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

    def test_seen_identity_blocks_new_url(self):
        from pipeline.state import compute_new_roles

        seen_role = {
            "company": "Google",
            "title": "Software Engineer Intern",
            "location": "Mountain View, CA",
            "url": "https://old.example/google",
        }
        current = [
            {
                "company": "Google",
                "title": "Software Engineer Intern",
                "location": "Mountain View, CA, USA",
                "url": "https://new.example/google",
            }
        ]
        seen = {role_key(seen_role): seen_role}
        assert compute_new_roles(current, seen, role_keys) == []


class TestUsLocation:
    def test_keeps_us_locations(self):
        assert is_us_location("San Mateo, CA")
        assert is_us_location("California, USA +7")
        assert is_us_location("Remote - USA")
        assert is_us_location("NYC")
        assert is_us_location("Texas")
        assert is_us_location("United States")
        assert is_us_location("CanadaUnited KingdomUnited States")
        assert is_us_location("Remote - New York City, NY +1")
        assert is_us_location("Dubai - United Arab EmiratesNYC")

    def test_drops_foreign_only(self):
        assert not is_us_location("London, UK")
        assert not is_us_location("Montreal, QC, Canada")
        assert not is_us_location("Remote in Canada")
        assert not is_us_location("Remote - Vancouver, Canada +3")
        assert not is_us_location("Yinchuan, China +1")
        assert not is_us_location("Asti, Italy +1")
        assert not is_us_location("Edinburgh, UK")

    def test_filter_roles_applies_us_and_title(self):
        roles = [
            {"title": "Software Engineer Intern", "location": "Seattle, WA"},
            {"title": "Software Engineer Intern", "location": "London, UK"},
            {"title": "Senior Software Engineer", "location": "Austin, TX"},
        ]
        kept, dropped = filter_roles(roles)
        assert [r["location"] for r in kept] == ["Seattle, WA"]
        assert len(dropped) == 2


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
        companies = {v["company"] for v in seen["roles"].values()}
        assert companies == {"Co"}
