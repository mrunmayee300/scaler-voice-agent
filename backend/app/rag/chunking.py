"""Semantic chunking utilities for ingestion."""

from typing import Any, Dict, List

from langchain_text_splitters import RecursiveCharacterTextSplitter


def create_semantic_splitter(
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )


def chunk_text(
    text: str,
    metadata: Dict[str, Any],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> List[Dict[str, Any]]:
    """Split text into chunks with metadata."""
    if not text or not text.strip():
        return []
    splitter = create_semantic_splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_text(text.strip())
    results = []
    for i, chunk in enumerate(chunks):
        chunk_meta = {
            **metadata,
            "chunk_id": f"{metadata.get('source', 'doc')}_{metadata.get('chunk_index', i)}_{i}",
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        results.append({"text": chunk, "metadata": chunk_meta})
    return results


def chunk_commit_message(
    repo: str,
    commit_hash: str,
    message: str,
    author: str,
    date: str,
    files_changed: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Create commit-specific chunks."""
    files_str = ", ".join(files_changed or [])[:500]
    text = (
        f"Repository: {repo}\n"
        f"Commit: {commit_hash}\n"
        f"Date: {date}\n"
        f"Author: {author}\n"
        f"Message: {message}\n"
        f"Files changed: {files_str}"
    )
    metadata = {
        "source": f"github_commit_{repo}",
        "source_type": "commit",
        "repo": repo,
        "commit_hash": commit_hash,
        "date": date,
        "file": files_str,
    }
    return chunk_text(text, metadata, chunk_size=600, chunk_overlap=50)
