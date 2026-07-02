# CanonKeeper — AI Story Continuity Engine

Writers and studios lose real time and money to continuity errors — a
character's eye color changes between chapters, a timeline contradicts
itself, a subplot quietly vanishes. CanonKeeper reads a manuscript,
builds a structured record of its characters, timeline, and established
facts, then flags contradictions and shows the exact passages that
conflict.

Built for the IBM SkillsBuild AI Builders Challenge (July 2026 —
Creative Industries theme).

## How it works

1. Upload a manuscript (PDF, DOCX, or TXT).
2. Docling parses it into clean, structured text.
3. The text is split into scene-sized chunks and embedded into a
   vector store (Qdrant).
4. IBM Granite (running locally via Ollama) extracts canon facts —
   characters, traits, locations, events — from each scene.
5. When a new passage contradicts an established fact, CanonKeeper
   flags it with cited evidence from both passages.

## Tech stack

- **AI / parsing:** IBM Granite (via Ollama, local), Docling
- **Backend:** FastAPI, Python
- **Data:** PostgreSQL (canon facts), Qdrant (vector search)
- **Frontend:** React + TypeScript (in progress)
- **Developed with:** IBM Bob

## Status

Work in progress — building through July 2026.

- [x] FastAPI backend with upload endpoint
- [ ] Docling ingestion + scene chunking
- [ ] Granite fact extraction
- [ ] Contradiction detection with cited evidence
- [ ] React dashboard

## Running locally
