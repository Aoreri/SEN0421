"""Checks a PR body against .github/pull_request_template.md.

Usage: PR_BODY="..." python check_pr_description.py   |   python check_pr_description.py --self-test
"""
import os
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "pull_request_template.md"
AGENT = re.compile(r"^Agent: (none|\S.* via \S.*)$")


def headings(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.startswith("## ")]


def check(body: str, template: str) -> list[str]:
    body = re.sub(r"<!--.*?-->", "", body.replace("\r\n", "\n"), flags=re.S)
    lines = [line.rstrip() for line in body.split("\n")]
    errors = []

    starts = {}
    for h in headings(template):
        if h in lines:
            starts[h] = lines.index(h)
        else:
            errors.append(f"Missing section: {h}")

    agent_at = next((i for i, line in enumerate(lines) if line.startswith("Agent:")), None)
    if agent_at is None:
        errors.append('Missing last line "Agent: <model> via <harness>" or "Agent: none"')
    elif not AGENT.match(lines[agent_at]):
        errors.append(f'Malformed agent line: "{lines[agent_at]}"; use "Agent: <model> via <harness>" or "Agent: none"')
    elif starts and agent_at < max(starts.values()):
        errors.append("The Agent line must come after every section")

    ends = [*starts.values(), len(lines)] + ([agent_at] if agent_at is not None else [])
    for h, start in starts.items():
        end = min(e for e in ends if e > start)
        content = "\n".join(lines[start + 1:end]).strip()
        if not content:
            errors.append(f"Empty section: {h}")
        elif h == "## Plan item" and not re.search(r"\b(PLN|WP)-\d+\b", content):
            errors.append("Plan item must name a PLN-xx or WP-xx id from the progress report")
    return errors


def self_test() -> None:
    t = TEMPLATE.read_text(encoding="utf-8")
    good = ("## Summary\nx\n## Plan item\nPLN-04\n## Standard\n12207\n## Verification\npytest\n"
            "## Database and deployment\nNone\n\nAgent: Claude Opus 5.5 via Claude Code\n\nfooter")
    assert check(good, t) == [], check(good, t)
    assert check(good.replace("Agent: Claude Opus 5.5 via Claude Code", "Agent: none"), t) == []
    assert check(t, t)  # the untouched template must fail
    assert "Empty section: ## Standard" in check(good.replace("12207", "<!-- c -->"), t)
    assert "Missing section: ## Verification" in check(good.replace("## Verification\n", ""), t)
    assert any("PLN-xx" in e for e in check(good.replace("PLN-04", "db stuff"), t))
    assert any("Malformed" in e for e in check(good.replace(" via Claude Code", ""), t))
    assert any("Missing last line" in e for e in check(good.replace("Agent:", "Model:"), t))
    assert any("after every section" in e
               for e in check("Agent: none\n" + good.split("\n\nAgent")[0], t))
    print("self-test ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        sys.exit()
    problems = check(os.environ.get("PR_BODY", ""), TEMPLATE.read_text(encoding="utf-8"))
    for p in problems:
        print(f"::error title=PR description::{p}")
    if problems:
        print("Fill in .github/pull_request_template.md; see AGENTS.md > Branches and pull requests.")
    sys.exit(1 if problems else 0)
