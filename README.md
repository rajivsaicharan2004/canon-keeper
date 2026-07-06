# CanonKeeper

CanonKeeper is an AI-powered continuity checker for fiction writers.

It analyzes story drafts, extracts canon facts, stores them in a vector database, and flags contradictions across scenes.

Example: if a character has green eyes in Scene 1 and blue eyes in Scene 3, CanonKeeper identifies the inconsistency, shows the conflicting quotes, and explains the issue.

## Features

- Upload story drafts for continuity analysis
- Extract structured facts from scenes
- Detect contradictions across character traits, object status, and story details
- Show source quotes for each conflict
- Use Qwen through Ollama for local LLM reasoning
- Use Qdrant for vector storage and retrieval
- Use Docling for document ingestion
- Modern React frontend with a clean writer-focused interface

## Demo Example

Sample input:

```text
Scene 1:
Elena entered the old observatory with green eyes shining under the moonlight.
She carried a silver compass given to her by her brother Marcus.

Scene 3:
Elena returned to the observatory at dawn.
Her blue eyes scanned the room as she searched for the missing compass.
