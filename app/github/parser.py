"""Parse GitHub API responses into internal Pydantic schemas."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.rstrip("Z"))


def parse_pull_request(data: dict) -> dict:
    """Convert a GitHub API PR response to a plain dict for PR creation."""
    labels = [label["name"] for label in data.get("labels", [])]
    return {
        "github_pr_number": data["number"],
        "title": data["title"],
        "author": data["user"]["login"],
        "url": data["html_url"],
        "labels": json.dumps(labels),
        "github_created_at": _parse_dt(data.get("created_at")),
        "github_state": data.get("state", "open"),
        "merged": bool(data.get("merged") or data.get("merged_at")),
        "draft": bool(data.get("draft", False)),
    }
