"""Uses the GitHub Contents API as a tiny key-value store for data that needs to survive
between two separate serverless invocations (the weekly cron job that generates the
newsletter draft, and the /newsletter page that displays it later) — Vercel functions
don't share a filesystem across invocations, but a git commit triggers Vercel's existing
auto-deploy-on-push, so the next page load picks up the new file naturally.
"""
import base64
import json

import requests

from . import config

API_BASE = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def read_json(path: str) -> dict | None:
    """Reads and parses a JSON file from the repo. Returns None if it doesn't exist yet."""
    config.require("GITHUB_TOKEN")
    url = f"{API_BASE}/repos/{config.GITHUB_REPO}/contents/{path}"
    resp = requests.get(url, headers=_headers(), params={"ref": config.GITHUB_BRANCH}, timeout=20)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    content_b64 = resp.json()["content"]
    return json.loads(base64.b64decode(content_b64))


def write_json(path: str, data: dict, message: str) -> None:
    """Creates or updates a JSON file in the repo, triggering Vercel's auto-deploy."""
    config.require("GITHUB_TOKEN")
    url = f"{API_BASE}/repos/{config.GITHUB_REPO}/contents/{path}"

    existing = requests.get(url, headers=_headers(), params={"ref": config.GITHUB_BRANCH}, timeout=20)
    sha = existing.json()["sha"] if existing.status_code == 200 else None

    content_b64 = base64.b64encode(json.dumps(data, indent=2).encode("utf-8")).decode("ascii")
    body = {"message": message, "content": content_b64, "branch": config.GITHUB_BRANCH}
    if sha:
        body["sha"] = sha

    resp = requests.put(url, headers=_headers(), json=body, timeout=20)
    resp.raise_for_status()
