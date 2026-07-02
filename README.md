# CanonKeeper — AI Story Continuity Engine

Writers and studios lose real time to continuity errors: a character's wound moves from shoulder to leg between chapters, an age drifts, an eye color changes. CanonKeeper reads a manuscript, builds a structured record of its characters and facts, and flags contradictions — showing the exact conflicting passages so a writer can fix them.

Built for the IBM SkillsBuild AI Builders Challenge (July 2026 — Creative Industries theme).

## What it does

Upload a manuscript (.txt, .pdf, or .docx). CanonKeeper then:

1. Parses the document into clean text with Docling.
2. Splits it into scene-sized chunks.
3. Extracts canon facts from each chunk with IBM Granite — structured statements like Watson · war wound location · left shoulder.
4. Embeds each fact with Granite's embedding model and stores it in a Qdrant vector database.
5. Detects contradictions by finding semantically similar facts and asking Granite to judge whether they genuinely conflict — reporting each with its source scenes as evidence.

## Why this design

Structured facts, not raw Q&A. Extracting atomic facts (entity · attribute · value) makes every finding traceable to a source scene and lets the tool scale to long documents.

Semantic search before AI judgment. Embeddings + Qdrant cheaply narrow the facts down to genuinely similar pairs; Granite then reasons only over those candidates. This lets it recognize that "Dr. Watson · war wound location" and "Watson · wound location" describe the same thing despite different wording.

Tuned for precision. A similarity threshold and a few-shot judge prompt run at temperature 0 keep false positives down.

Local and private. Granite runs locally via Ollama, so unpublished manuscripts never leave the author's machine.

## Tech stack

- Document parsing: Docling
- Reasoning + extraction: IBM Granite (granite4:micro) via Ollama
- Embeddings: granite-embedding:278m via Ollama
- Vector store: Qdrant Cloud
- Backend: FastAPI (Python)
- Frontend: React + TypeScript (Vite)

## Architecture

Manuscript -> Docling parse + chunk -> Scene chunks -> Granite extraction -> Canon facts -> Granite embeddings -> Qdrant vector store -> semantic search + Granite judge -> Contradictions (with cited scenes)

## Running locally

Prerequisites: Python 3.11+, Node.js 18+, Ollama (https://ollama.com), and a Qdrant Cloud account.

1. Pull the models:

    ollama pull granite4:micro
    ollama pull granite-embedding:278m

2. Backend:

    python -m venv .venv
    source .venv/bin/activate
    pip install -r backend/requirements.txt

Create a .env file in the project root with QDRANT_URL and QDRANT_API_KEY, then:

    uvicorn backend.app.main:app --reload

API docs at http://localhost:8000/docs

3. Frontend:

    cd frontend
    npm install
    npm run dev

App at http://localhost:5173

## Project structure

- backend/app/ingestion.py — Docling parsing and scene chunking
- backend/app/extraction.py — Granite fact extraction with robust JSON parsing
- backend/app/vectors.py — Granite embeddings and Qdrant storage
- backend/app/detector.py — semantic candidate search + Granite contradiction judging
- backend/app/main.py — FastAPI endpoints (/upload, /analyze, /entities)
- frontend/src/App.tsx — upload, analyze, and results UI

## Status and known limitations

- Extraction quality depends on the local model; granite4:micro is fast but sometimes labels the same property inconsistently, which can cause some real contradictions to be missed on longer documents.
- Results can vary slightly between runs due to model non-determinism.
- Tuning (chunk size, similarity threshold, neighbor count) trades recall against precision and speed; current settings favor precision.

## Future work

- Attribute normalization so differently-worded properties cluster reliably.
- A knowledge-graph view of characters and their facts across a story.
- A canon-safe writing assistant that checks new drafts against established facts in real time.
