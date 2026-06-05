#!/usr/bin/env python3
"""Ingest GitHub repository READMEs and project metadata."""

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
from app.rag.chunking import chunk_text
from ingestion.utils import embed_and_store

GITHUB_API = "https://api.github.com"


async def fetch_repo_data(
    username: str,
    repo: str,
    token: str,
) -> dict | None:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=30) as client:
        repo_resp = await client.get(f"{GITHUB_API}/repos/{username}/{repo}", headers=headers)
        if repo_resp.status_code != 200:
            print(f"Failed to fetch {repo}: {repo_resp.status_code}")
            return None
        repo_data = repo_resp.json()

        readme_resp = await client.get(
            f"{GITHUB_API}/repos/{username}/{repo}/readme",
            headers={**headers, "Accept": "application/vnd.github.raw"},
        )
        readme = readme_resp.text if readme_resp.status_code == 200 else ""

        # Fetch issues (open, max 20)
        issues_resp = await client.get(
            f"{GITHUB_API}/repos/{username}/{repo}/issues",
            headers=headers,
            params={"state": "all", "per_page": 20},
        )
        issues = []
        if issues_resp.status_code == 200:
            for issue in issues_resp.json():
                if "pull_request" not in issue:
                    issues.append(f"#{issue['number']}: {issue['title']} ({issue['state']})")

        return {
            "name": repo_data["name"],
            "description": repo_data.get("description", ""),
            "language": repo_data.get("language", ""),
            "topics": repo_data.get("topics", []),
            "stars": repo_data.get("stargazers_count", 0),
            "url": repo_data["html_url"],
            "readme": readme,
            "issues": issues,
        }


async def ingest_github_repos(
    username: str | None = None,
    repos: List[str] | None = None,
) -> int:
    settings = get_settings()
    username = username or os.getenv("GITHUB_USERNAME", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not username or not token:
        print("Set GITHUB_USERNAME and GITHUB_TOKEN in .env")
        return 0

    repo_list = repos or os.getenv("GITHUB_REPOS", "").split(",")
    repo_list = [r.strip() for r in repo_list if r.strip()]
    if not repo_list:
        print("Set GITHUB_REPOS in .env (comma-separated)")
        return 0

    readme_chunks = []
    project_chunks = []

    for repo in repo_list:
        print(f"Fetching {username}/{repo}...")
        data = await fetch_repo_data(username, repo, token)
        if not data:
            continue

        # README collection
        if data["readme"]:
            readme_text = (
                f"Repository: {data['name']}\n"
                f"URL: {data['url']}\n"
                f"Language: {data['language']}\n"
                f"Description: {data['description']}\n\n"
                f"{data['readme']}"
            )
            meta = {
                "source": f"github_readme_{repo}",
                "source_type": "github_readme",
                "repo": repo,
                "file": "README.md",
            }
            readme_chunks.extend(chunk_text(readme_text, meta))

        # Projects collection
        project_text = (
            f"Project: {data['name']}\n"
            f"Repository: {data['url']}\n"
            f"Language: {data['language']}\n"
            f"Topics: {', '.join(data['topics'])}\n"
            f"Stars: {data['stars']}\n"
            f"Description: {data['description']}\n"
        )
        if data["issues"]:
            project_text += f"\nIssues:\n" + "\n".join(data["issues"])

        project_meta = {
            "source": f"github_project_{repo}",
            "source_type": "project",
            "repo": repo,
        }
        project_chunks.extend(chunk_text(project_text, project_meta, chunk_size=600))

    total = 0
    if readme_chunks:
        c = await embed_and_store(settings.collections["github_readmes"], readme_chunks)
        print(f"Stored {c} README chunks")
        total += c
    if project_chunks:
        c = await embed_and_store(settings.collections["projects"], project_chunks)
        print(f"Stored {c} project chunks")
        total += c
    return total


if __name__ == "__main__":
    asyncio.run(ingest_github_repos())
