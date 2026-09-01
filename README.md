# GitHub Internship Alerts

Daily monitor for internship listings posted on GitHub README repos. Compares against a persistent `seen.json` and emails you only roles that have never appeared before.

## Sources (configured in `sources.yaml`)

| Source | What it watches |
|---|---|
| **SpeedyApply internships** | `README.md` - FAANG+ and Other sections |
| **SpeedyApply new grad** | `NEW_GRAD_USA.md` - FAANG+ and Other, title-filtered |
| **SimplifyJobs** | `Summer2027-Internships` README - all categories |

Cross-repo overlap is handled automatically: same apply URL **or** same company + title + location counts as one role. Roles already in `seen.json` are not emailed again.

## Title and location filter

After parsing, titles must look like intern / analyst / early career (or co-op, student, apprentice, rotational). Dropped:

- SWE I / SWE II / Software Engineer I / Engineer II and similar
- Generic new-grad SWE titles with none of the keywords above
- Master's / PhD / years-of-experience / senior / staff in the title (internships are kept)

This only sees the **title** on the GitHub list, not the job description, so a posting titled "Software Engineer Intern" that requires a master's in the JD will still come through.

Locations must look US-based (city + state, USA, NYC, Remote - USA). Mixed lists that include a US office are kept. Canada / UK / EU / China / remote-in-Canada only are dropped. Bare "Remote" with no country is kept.

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

The first run records every current listing in `seen.json` without flooding your inbox. You get one init email: *"Recorded N existing listings - future emails are new only."*

## Local test (no email)

```bash
python -c "
from adapters.github_fetch import fetch_markdown
from adapters.speedyapply import parse_speedyapply
from adapters.simplify import parse_simplify
from pipeline.dedupe import dedupe_roles
from pipeline.filter import filter_roles

sa_intern = parse_speedyapply(fetch_markdown('speedyapply/2027-SWE-College-Jobs', 'README.md'), ['FAANG+', 'Other'])
sa_ng = parse_speedyapply(fetch_markdown('speedyapply/2027-SWE-College-Jobs', 'NEW_GRAD_USA.md'), ['FAANG+', 'Other'])
si = parse_simplify(fetch_markdown('SimplifyJobs/Summer2027-Internships', 'README.md', 'dev'))
kept, dropped = filter_roles(sa_intern + sa_ng + si)
all_roles = dedupe_roles(kept)
print(f'interns: {len(sa_intern)}, new grad: {len(sa_ng)}, simplify: {len(si)}')
print(f'kept: {len(kept)}, dropped: {len(dropped)}, unique: {len(all_roles)}')
"
```

## Adding sources

Edit `sources.yaml`. Supported types:

- `speedyapply` - markdown tables with `### Section` headers; set `sections: [...]`
- `simplify` - HTML tables in README; parses all sections
