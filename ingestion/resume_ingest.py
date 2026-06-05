#!/usr/bin/env python3
"""Ingest resume PDF into Qdrant resume collection."""

import asyncio
import os
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import get_settings
from app.rag.chunking import chunk_text
from ingestion.utils import embed_and_store


def extract_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


async def ingest_resume(pdf_path: str | None = None) -> int:
    settings = get_settings()
    path = pdf_path or os.getenv("RESUME_PDF_PATH", "./data/resume/resume.pdf")
    if not Path(path).exists():
        print(f"Resume not found at {path}. Place your resume PDF there.")
        return 0

    print(f"Parsing resume: {path}")
    text = extract_pdf_text(path)
    metadata = {
        "source": "resume",
        "source_type": "resume",
        "file": Path(path).name,
    }
    chunks = chunk_text(text, metadata, chunk_size=800, chunk_overlap=150)
    print(f"Created {len(chunks)} chunks")

    collection = settings.collections["resume"]
    count = await embed_and_store(collection, chunks)
    print(f"Stored {count} chunks in {collection}")
    return count


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(ingest_resume(path))
