"""Benchmark dataset generator for CareerVerse evaluation.

Generates a realistic benchmark of labeled open-source issues across held-out
repositories in 5 languages (Python, TypeScript, Go, Rust, Java), with labels:
  - ACTIONABLE_NOW (High-quality starter issue, clear steps, unassigned, active repo)
  - PROMISING_BUT_UNCLEAR (Valid issue but needs maintainer clarification)
  - BLOCKED_OR_CLAIMED (Claimed in comments or has open linked PR)
  - NOT_SUITABLE (Stale repo, closed, duplicate, or trivial noise)
  - PULL_REQUEST (Pull request included in label-only queries)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

OUTPUT_PATH = Path(__file__).parent.parent / "fixtures" / "benchmark_issues.json"


def generate_dataset() -> list[dict[str, Any]]:
    now = datetime.now(tz=UTC)
    issues: list[dict[str, Any]] = []

    # Held-out repositories and their health metadata
    repos = {
        "fastapi/fastapi": {
            "stars": 75000,
            "forks": 6200,
            "open_issues": 320,
            "language": "Python",
            "pushed_days_ago": 2,
            "license": "MIT",
        },
        "facebook/react": {
            "stars": 225000,
            "forks": 45000,
            "open_issues": 750,
            "language": "TypeScript",
            "pushed_days_ago": 1,
            "license": "MIT",
        },
        "gin-gonic/gin": {
            "stars": 77000,
            "forks": 8000,
            "open_issues": 150,
            "language": "Go",
            "pushed_days_ago": 3,
            "license": "MIT",
        },
        "tokio-rs/tokio": {
            "stars": 26000,
            "forks": 2400,
            "open_issues": 210,
            "language": "Rust",
            "pushed_days_ago": 2,
            "license": "MIT",
        },
        "spring-projects/spring-boot": {
            "stars": 74000,
            "forks": 40000,
            "open_issues": 480,
            "language": "Java",
            "pushed_days_ago": 1,
            "license": "Apache-2.0",
        },
        # Held-out stale or abandoned repositories
        "abandoned-org/old-tool": {
            "stars": 250,
            "forks": 30,
            "open_issues": 180,
            "language": "Python",
            "pushed_days_ago": 780,  # > 2 years stale
            "license": "MIT",
        },
        "unmaintained/legacy-ts": {
            "stars": 120,
            "forks": 15,
            "open_issues": 90,
            "language": "TypeScript",
            "pushed_days_ago": 650,  # > 1.5 years stale
            "license": None,
        },
    }

    issue_id_counter = 1000

    for repo_name, repo_meta in repos.items():
        lang = repo_meta["language"]
        is_stale_repo = repo_meta["pushed_days_ago"] > 180

        # 1. High quality ACTIONABLE_NOW issues (10 per active repo)
        if not is_stale_repo:
            for i in range(1, 11):
                issue_id_counter += 1
                updated_at = now - timedelta(days=i)
                issues.append({
                    "id": issue_id_counter,
                    "issue_key": f"{repo_name}#{issue_id_counter}",
                    "repository": repo_name,
                    "number": issue_id_counter,
                    "html_url": f"https://github.com/{repo_name}/issues/{issue_id_counter}",
                    "repository_url": f"https://api.github.com/repos/{repo_name}",
                    "title": f"[{lang}] Add structured validation for handler parameters in sub-module {i}",
                    "body": (
                        "### Problem\n"
                        "When passing invalid parameters, the endpoint raises an uncaught internal error.\n\n"
                        "### Steps to Reproduce\n"
                        "```python\n"
                        "client.get('/api/test?invalid=param')\n"
                        "```\n\n"
                        "### Expected Behavior\n"
                        "- [ ] Returns HTTP 422 with validation loc details\n"
                        "- [ ] Add unit test in `tests/test_validation.py`\n\n"
                        "### Context\n"
                        "See file `router/validation.py` line 45 for reference."
                    ),
                    "state": "open",
                    "state_reason": None,
                    "locked": False,
                    "is_pr": False,
                    "labels": ["good first issue", "help wanted", lang.lower()],
                    "is_assigned": False,
                    "assignee_count": 0,
                    "comments_count": 2,
                    "created_at": (now - timedelta(days=15)).isoformat(),
                    "updated_at": updated_at.isoformat(),
                    "author_association": "MEMBER",
                    "ground_truth_label": "ACTIONABLE_NOW",
                    "repo_metadata": repo_meta,
                })

        # 2. BLOCKED_OR_CLAIMED issues (has "good first issue" label, but someone claimed it or linked PR exists)
        for i in range(1, 4):
            issue_id_counter += 1
            updated_at = now - timedelta(days=i * 3)
            issues.append({
                "id": issue_id_counter,
                "issue_key": f"{repo_name}#{issue_id_counter}",
                "repository": repo_name,
                "number": issue_id_counter,
                "html_url": f"https://github.com/{repo_name}/issues/{issue_id_counter}",
                "repository_url": f"https://api.github.com/repos/{repo_name}",
                "title": f"[{lang}] Implement helper utility {i} for CLI commands",
                "body": (
                    "Would be great to add a helper function here.\n\n"
                    "Comment: I am working on this right now! Submitting PR tomorrow."
                ),
                "state": "open",
                "state_reason": None,
                "locked": False,
                "is_pr": False,
                "labels": ["good first issue", "help wanted"],
                "is_assigned": True,
                "assignee_count": 1,
                "comments_count": 5,
                "created_at": (now - timedelta(days=20)).isoformat(),
                "updated_at": updated_at.isoformat(),
                "author_association": "NONE",
                "ground_truth_label": "BLOCKED_OR_CLAIMED",
                "repo_metadata": repo_meta,
            })

        # 3. PULL_REQUEST entries that contaminated search queries (GitHub search returns PRs under is:issue)
        for i in range(1, 4):
            issue_id_counter += 1
            issues.append({
                "id": issue_id_counter,
                "issue_key": f"{repo_name}#{issue_id_counter}",
                "repository": repo_name,
                "number": issue_id_counter,
                "html_url": f"https://github.com/{repo_name}/issues/{issue_id_counter}",
                "repository_url": f"https://api.github.com/repos/{repo_name}",
                "title": f"PR: Fix router parameter parsing for {lang} issue #{i}",
                "body": "Closes #123. Implements the fix.",
                "state": "open",
                "state_reason": None,
                "locked": False,
                "is_pr": True,  # Pull request!
                "pull_request": {"url": f"https://api.github.com/repos/{repo_name}/pulls/{issue_id_counter}"},
                "labels": ["good first issue"],
                "is_assigned": False,
                "assignee_count": 0,
                "comments_count": 1,
                "created_at": (now - timedelta(days=10)).isoformat(),
                "updated_at": (now - timedelta(days=2)).isoformat(),
                "author_association": "CONTRIBUTOR",
                "ground_truth_label": "NOT_SUITABLE",
                "repo_metadata": repo_meta,
            })

        # 4. PROMISING_BUT_UNCLEAR issues (Valid idea, but vague 1-sentence body, no repro steps, missing acceptance criteria)
        for i in range(1, 4):
            issue_id_counter += 1
            issues.append({
                "id": issue_id_counter,
                "issue_key": f"{repo_name}#{issue_id_counter}",
                "repository": repo_name,
                "number": issue_id_counter,
                "html_url": f"https://github.com/{repo_name}/issues/{issue_id_counter}",
                "repository_url": f"https://api.github.com/repos/{repo_name}",
                "title": f"Refactor module {i} maybe?",
                "body": "It would be nice if we could make this faster.",
                "state": "open",
                "state_reason": None,
                "locked": False,
                "is_pr": False,
                "labels": ["good first issue"],
                "is_assigned": False,
                "assignee_count": 0,
                "comments_count": 0,
                "created_at": (now - timedelta(days=40)).isoformat(),
                "updated_at": (now - timedelta(days=35)).isoformat(),
                "author_association": "NONE",
                "ground_truth_label": "PROMISING_BUT_UNCLEAR",
                "repo_metadata": repo_meta,
            })

        # 5. Stale / Closed / Duplicate / Not suitable issues
        for i in range(1, 4):
            issue_id_counter += 1
            issues.append({
                "id": issue_id_counter,
                "issue_key": f"{repo_name}#{issue_id_counter}",
                "repository": repo_name,
                "number": issue_id_counter,
                "html_url": f"https://github.com/{repo_name}/issues/{issue_id_counter}",
                "repository_url": f"https://api.github.com/repos/{repo_name}",
                "title": f"Old stale report {i}",
                "body": "Doesn't work on Python 2.7.",
                "state": "closed" if i % 2 == 0 else "open",
                "state_reason": "completed" if i % 2 == 0 else None,
                "locked": False,
                "is_pr": False,
                "labels": ["good first issue", "wontfix"] if i % 2 != 0 else ["duplicate"],
                "is_assigned": False,
                "assignee_count": 0,
                "comments_count": 1,
                "created_at": (now - timedelta(days=400)).isoformat(),
                "updated_at": (now - timedelta(days=350)).isoformat(),
                "author_association": "NONE",
                "ground_truth_label": "NOT_SUITABLE",
                "repo_metadata": repo_meta,
            })

    return issues


if __name__ == "__main__":
    data = generate_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data)} benchmark issues at {OUTPUT_PATH}")
