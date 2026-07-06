from __future__ import annotations

import os
from pathlib import Path


ALLOWED_TEXT = {".txt", ".md"}
ALLOWED_DOCLING = {".pdf", ".docx", ".pptx", ".html"}


def parse_document(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in ALLOWED_TEXT:
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix in ALLOWED_DOCLING:
        if os.getenv("DISABLE_DOCLING", "false").lower() == "true":
            raise ValueError(
                "Document parsing is disabled in the hosted demo. "
                "Please upload a .txt or .md file."
            )

        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(path))
        return result.document.export_to_markdown()

    raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[dict]:
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    index = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append({"index": index, "text": chunk})

        index += 1
        start = max(end - overlap, end)

    return chunks


def ingest(file_path: str) -> list[dict]:
    clean_text = parse_document(file_path)
    return chunk_text(clean_text)
