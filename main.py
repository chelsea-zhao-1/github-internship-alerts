import sys
import yaml
from datetime import datetime, timezone

from adapters.github_fetch import fetch_markdown
from adapters.speedyapply import parse_speedyapply
from adapters.simplify import parse_simplify
from pipeline.dedupe import dedupe_roles, role_key
from pipeline.state import build_snapshot, compute_new_roles, load_state, save_state
from notify.gmail import send_email

PARSERS = {
    "speedyapply": lambda source, content: parse_speedyapply(
        content, source.get("sections", [])
    ),
    "simplify": lambda source, content: parse_simplify(content),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_role(role: dict, index: int) -> str:
    lines = [
        f"{index}. {role['company']} - {role['title']}",
        f"   Location: {role['location']}",
    ]
    if role.get("section"):
        lines.append(f"   Section: {role['section']}")
    if role.get("source"):
        lines.append(f"   Source: {role['source']}")
    if role.get("age"):
        lines.append(f"   Posted: {role['age']} ago")
    if role.get("url"):
        lines.append(f"   Apply: {role['url']}")
    return "\n".join(lines)


def _send_init_email(total_roles: int, timestamp: str) -> None:
    body = (
        f"GitHub internship monitor initialized.\n\n"
        f"Recorded {total_roles} existing listing(s) across your configured repos. "
        f"They will not be emailed again.\n\n"
        f"Starting tomorrow, you'll receive a daily email with only roles "
        f"that appear for the first time.\n\n"
        f"---\nInitialized at {timestamp}."
    )
    send_email("GitHub internship monitor initialized", body)


def _send_update_email(new_roles: list[dict], timestamp: str) -> None:
    date_str = timestamp[:10]
    if new_roles:
        subject = f"{len(new_roles)} new GitHub internship listing(s) - {date_str}"
        body_lines = [
            _format_role(role, i + 1)
            for i, role in enumerate(new_roles)
        ]
        body = (
            "\n\n".join(body_lines)
            + f"\n\n---\nChecked at {timestamp}."
        )
    else:
        subject = f"No new GitHub internship listings - {date_str}"
        body = (
            "No new listings since the last check.\n\n"
            f"---\nChecked at {timestamp}."
        )
    send_email(subject, body)


def _send_error_email(display_name: str, error: str, timestamp: str) -> None:
    body = (
        f"Error while checking {display_name}:\n{error}\n\n"
        f"Previous seen-state was preserved.\n\n"
        f"---\nAttempted at {timestamp}."
    )
    send_email(f"GitHub internship monitor error - {timestamp[:10]}", body)


def _fetch_source_roles(source: dict) -> list[dict]:
    parser = PARSERS.get(source["type"])
    if parser is None:
        raise ValueError(f"Unknown source type '{source['type']}'")

    content = fetch_markdown(
        repo=source["repo"],
        path=source["path"],
        branch=source.get("branch", "main"),
    )
    roles = parser(source, content)
    for role in roles:
        role["source"] = source["display_name"]
    return roles


def main() -> int:
    with open("sources.yaml") as f:
        config = yaml.safe_load(f)

    state, is_cold_start = load_state()
    timestamp = _now_iso()
    overall_status = "success"
    fetch_errors: list[str] = []

    all_roles: list[dict] = []
    for source in config["sources"]:
        name = source["name"]
        display = source["display_name"]
        print(f"[{name}] Fetching {source['repo']}/{source['path']}...")
        try:
            roles = _fetch_source_roles(source)
        except Exception as exc:
            msg = str(exc)
            print(f"[{name}] Error: {msg}")
            fetch_errors.append(f"{display}: {msg}")
            overall_status = "fetch_error"
            try:
                _send_error_email(display, msg, timestamp)
            except Exception as notify_err:
                print(f"[{name}] Also failed to send error email: {notify_err}")
            continue

        print(f"[{name}] Parsed {len(roles)} role(s).")
        all_roles.extend(roles)

    unique_roles = dedupe_roles(all_roles)
    print(f"[main] {len(unique_roles)} unique role(s) after cross-repo dedup.")

    if is_cold_start:
        if fetch_errors and not unique_roles:
            state["last_status"] = overall_status
            save_state(state)
            return 1

        try:
            _send_init_email(len(unique_roles), timestamp)
        except Exception as exc:
            print(f"[main] Failed to send init email: {exc}")
            state["last_status"] = "notify_error"
            save_state(state)
            return 1

        state["initialized_at"] = timestamp
        state["roles"] = build_snapshot(unique_roles, {}, role_key, timestamp)
        state["last_status"] = overall_status
        save_state(state)
        print(f"[main] Cold start complete. Recorded {len(unique_roles)} role(s).")
        return 0 if overall_status == "success" else 1

    new_roles = compute_new_roles(unique_roles, state.get("roles", {}), role_key)
    print(f"[main] {len(new_roles)} new role(s) detected.")

    try:
        _send_update_email(new_roles, timestamp)
    except Exception as exc:
        print(f"[main] Failed to send update email: {exc}")
        state["last_status"] = "notify_error"
        save_state(state)
        return 1

    state["roles"] = build_snapshot(unique_roles, state.get("roles", {}), role_key, timestamp)
    state["last_status"] = overall_status
    save_state(state)
    print(f"[main] Done. Status: {overall_status}")
    return 0 if overall_status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
