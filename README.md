# GitHub Internship Alerts

Daily monitor for internship listings posted on GitHub README repos. Compares against a persistent `seen.json` and emails you only roles that have never appeared before.

## Sources (configured in `sources.yaml`)

| Source | What it watches |
|---|---|
| **SpeedyApply** | `NEW_GRAD_USA.md` — FAANG+ and Other sections only |
| **SimplifyJobs** | `Summer2027-Internships` README — all categories |

Cross-repo overlap is handled automatically (same apply URL = same role).

## Setup

```bash
cd ~/coding/github-internship-alerts
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Gmail (one-time)

If you already set up Gmail for `internship-scout`, reuse the same three GitHub secrets.

```bash
python setup_gmail.py   # only if you need a fresh token
```

### GitHub Actions secrets

| Secret | Value |
|---|---|
| `GMAIL_CREDENTIALS` | contents of `credentials.json` |
| `GMAIL_TOKEN` | contents of `token.json` |
| `NOTIFY_EMAIL` | your email |

Push to GitHub and the workflow runs every morning at **7 AM ET**.

### First run behavior

The first run records every current listing in `seen.json` without flooding your inbox. You get one init email: *"Recorded N existing listings — future emails are new only."*

## Local test (no email)

```bash
python -c "
from adapters.github_fetch import fetch_markdown
from adapters.speedyapply import parse_speedyapply
from adapters.simplify import parse_simplify
from pipeline.dedupe import dedupe_roles

sa = parse_speedyapply(fetch_markdown('speedyapply/2027-SWE-College-Jobs', 'NEW_GRAD_USA.md'), ['FAANG+', 'Other'])
si = parse_simplify(fetch_markdown('SimplifyJobs/Summer2027-Internships', 'README.md', 'dev'))
all_roles = dedupe_roles(sa + si)
print(f'SpeedyApply: {len(sa)}, Simplify: {len(si)}, unique: {len(all_roles)}')
"
```

## Adding sources

Edit `sources.yaml`. Supported types:

- `speedyapply` — markdown tables with `### Section` headers; set `sections: [...]`
- `simplify` — HTML tables in README; parses all sections
