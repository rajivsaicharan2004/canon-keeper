import traceback
"""FastAPI entrypoint for the Canon Keeper backend pipeline."""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
from uuid import uuid4

from app.ingestion import ingest
from app.extraction import extract_all
from app.vectors import store_facts
from app.detector import find_contradictions
from app.response_normalizer import normalize_analysis_response

# Create the app. The title shows up on the /docs page.
app = FastAPI(title="Canon Keeper API", version="0.1.0")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print("UNHANDLED ERROR:", repr(exc))
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_type": exc.__class__.__name__},
        headers={"Access-Control-Allow-Origin": "*"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://canon-keeper-frontend.vercel.app",
        "https://canon-keeper-frontend-7kbdm7mw4-charan23.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# CORS = Cross-Origin Resource Sharing. Browsers block a webpage on one
# address (our React app at :5173) from calling a server on another
# address (:8000) unless the server explicitly allows it. This does that.

# Where uploaded manuscripts get stored. Path() is Python's modern way to
# handle file paths so it works on Mac/Windows/Linux alike.
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)  # create folder if missing

# Only accept real document types — reject anything else.
ALLOWED = {".txt", ".md", ".pdf", ".docx", ".pptx", ".html"}


@app.get("/health")
def health():
    # A simple dict; FastAPI auto-converts it to JSON.
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    original_name = Path(file.filename or "upload.txt").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {suffix}")

    safe_name = f"{uuid4().hex}{suffix}"
    dest = UPLOAD_DIR / safe_name
    contents = await file.read()
    dest.write_bytes(contents)

    return {
        "filename": safe_name,
        "original_filename": original_name,
        "size_bytes": len(contents),
    }


@app.post("/analyze")
def analyze(filename: str):
    """
    Run the full CanonKeeper pipeline on an uploaded file:
    parse → chunk → extract facts → embed & store → detect contradictions.
    """
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Upload it first.")

    # 1. Parse the document and split it into scene-sized chunks.
    chunks = ingest(str(file_path))

    # 2. Have Granite extract structured canon facts from each chunk.
    facts = extract_all(chunks)

    # 3. Embed each fact and store it in the Qdrant vector database.
    stored = store_facts(facts)

    # 4. Find contradictions using semantic search + Granite judgment.
    contradictions = find_contradictions(facts)

    return normalize_analysis_response(locals())


@app.get("/entities")
def entities():
    """Return all canon facts currently stored in the vector database."""
    from app.vectors import _client, COLLECTION

    try:
        # scroll() pages through all stored points without a search query.
        points, _ = _client.scroll(collection_name=COLLECTION, limit=1000)
        return {"facts": [p.payload for p in points]}
    except Exception:
        return {"facts": []}  # collection may not exist yet
