"""Document ingestion: parses uploaded files and splits them into chunkable text."""

from pathlib import Path
from docling.document_converter import DocumentConverter

# One converter instance, reused. It loads ML models on first use (slow),
# so we don't want to recreate it on every request.
_converter = DocumentConverter()


def parse_document(file_path: str) -> str:
    """
    Turn a file (PDF/DOCX/TXT) into clean text.
    Docling reconstructs reading order and structure, then we export to
    Markdown — headings become '#', paragraphs are separated by blank lines.
    """
    result = _converter.convert(file_path)
    return result.document.export_to_markdown()


def chunk_text(text: str, max_chars: int = 400) -> list[dict]:
    """
    Split clean text into scene-sized chunks.

    Strategy: split on blank lines (paragraph breaks), then greedily group
    paragraphs until adding the next one would exceed max_chars, then start
    a fresh chunk. This keeps related sentences together instead of cutting
    mid-thought.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) > max_chars:
            chunks.append(current)   # seal the current chunk
            current = para           # start a new one
        else:
            current = f"{current}\n\n{para}" if current else para

    if current:                      # don't lose the final chunk
        chunks.append(current)

    # Index each chunk so we can cite "chunk #3" later.
    return [{"index": i, "text": c} for i, c in enumerate(chunks)]


def ingest(file_path: str) -> list[dict]:
    """Full pipeline: parse the file, then chunk it."""
    clean_text = parse_document(file_path)
    return chunk_text(clean_text)
