#!/usr/bin/env python3
"""Ingest GitHub commit history via API."""

import asyncio
import os
import sys
from pathlib import Path
from typing import List

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import get_settings
from app.rag.chunking import chunk_commit_message
from ingestion.utils import embed_and_store

GITHUB_API = "https://api.github.com"


async def fetch_commits(
    username: str,
    repo: str,
    token: str,
    max_commits: int = 100,
) -> List[dict]:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    commits = []
    page = 1
    async with httpx.AsyncClient(timeout=30) as client:
        while len(commits) < max_commits:
            resp = await client.get(
                f"{GITHUB_API}/repos/{username}/{repo}/commits",
                headers=headers,
                params={"per_page": 100, "page": page},
            )
            if resp.status_code != 200 or not resp.json():
                break
            for c in resp.json():
                commit_data = c.get("commit", {})
                files = []
                detail_resp = await client.get(
                    f"{GITHUB_API}/repos/{username}/{repo}/commits/{c['sha']}",
                    headers=headers,
                )
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    files = [f["filename"] for f in detail.get("files", [])[:10]]
                commits.append({
                    "hash": c["sha"][:12],
                    "message": commit_data.get("message", ""),
                    "author": commit_data.get("author", {}).get("name", ""),
                    "date": commit_data.get("author", {}).get("date", ""),
                    "files": files,
                })
                if len(commits) >= max_commits:
                    break
            page += 1
            if len(resp.json()) < 100:
                break
    return commits


async def ingest_commits(
    username: str | None = None,
    repos: List[str] | None = None,
    max_per_repo: int = 50,
) -> int:
    settings = get_settings()
    username = username or os.getenv("GITHUB_USERNAME", "")
    token = os.getenv("GITHUB_TOKEN", "")
    repo_list = repos or os.getenv("GITHUB_REPOS", "").split(",")
    repo_list = [r.strip() for r in repo_list if r.strip()]

    all_chunks = []
    for repo in repo_list:
        print(f"Fetching commits for {username}/{repo}...")
        commits = await fetch_commits(username, repo, token, max_per_repo)
        print(f"  Found {len(commits)} commits")
        for commit in commits:
            chunks = chunk_commit_message(
                repo=repo,
                commit_hash=commit["hash"],
                message=commit["message"],
                author=commit["author"],
                date=commit["date"],
                files_changed=commit["files"],
            )
            all_chunks.extend(chunks)

    if not all_chunks:
        return 0
    count = await embed_and_store(settings.collections["commits"], all_chunks)
    print(f"Stored {count} commit chunks")
    return count


if __name__ == "__main__":
    asyncio.run(ingest_commits())
