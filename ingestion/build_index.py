#!/usr/bin/env python3
"""Run full ingestion pipeline: resume + GitHub + commits."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from ingestion.resume_ingest import ingest_resume
from ingestion.github_ingest import ingest_github_repos
from ingestion.commit_ingest import ingest_commits


async def build_full_index(skip_resume: bool = False, skip_github: bool = False):
    print("=" * 60)
    print("AI Voice Assistant - Full Index Build")
    print("=" * 60)

    resume_count = 0
    github_count = 0
    commit_count = 0

    if skip_resume:
        print("\n[1/3] Skipping resume (already indexed)")
    else:
        print("\n[1/3] Ingesting resume...")
        resume_count = await ingest_resume()

    if skip_github:
        print("\n[2/3] Skipping GitHub (already indexed)")
    else:
        print("\n[2/3] Ingesting GitHub repos...")
        github_count = await ingest_github_repos()

    print("\n[3/3] Ingesting commit history...")
    commit_count = await ingest_commits()

    total = resume_count + github_count + commit_count
    print("\n" + "=" * 60)
    print(f"Index build complete. Total chunks: {total}")
    print(f"  Resume: {resume_count}")
    print(f"  GitHub: {github_count}")
    print(f"  Commits: {commit_count}")
    print("=" * 60)


async def build_commits_only():
    """Re-run commit ingestion when resume/GitHub already succeeded."""
    await build_full_index(skip_resume=True, skip_github=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Qdrant knowledge index")
    parser.add_argument(
        "--commits-only",
        action="store_true",
        help="Only ingest commit history (skip resume + GitHub)",
    )
    args = parser.parse_args()
    if args.commits_only:
        asyncio.run(build_commits_only())
    else:
        asyncio.run(build_full_index())
