from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from backend.app.ingestion import ingest
from backend.app.extraction import extract_all

# Create the app. The title shows up on the /docs page.
app = FastAPI(title="Canon Keeper API", version="0.1.0")

# CORS = Cross-Origin Resource Sharing. Browsers block a webpage on one
# address (our React app at :5173) from calling a server on another
# address (:8000) unless the server explicitly allows it. This does that.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Where uploaded manuscripts get stored. Path() is Python's modern way to
# handle file paths so it works on Mac/Windows/Linux alike.
UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)  # create folder if missing

# Only accept real document types — reject anything else.
ALLOWED = {".pdf", ".docx", ".txt"}


@app.get("/health")
def health():
    # A simple dict; FastAPI auto-converts it to JSON.
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # file.filename is the original name, e.g. "sherlock.txt"
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED:
        # 400 = "bad request." We refuse unsupported file types.
        raise HTTPException(status_code=400, detail=f"Unsupported type: {suffix}")

    # Read the raw bytes the browser sent, then write them to our folder.
    contents = await file.read()
    dest = UPLOAD_DIR / file.filename
    dest.write_bytes(contents)

    # Report back what we saved. len(contents) is the size in bytes.
    return {"filename": file.filename, "size_bytes": len(contents)}


@app.post("/analyze")
def analyze(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Upload it first.")

    chunks = ingest(str(file_path))
    facts = extract_all(chunks)

    return {
        "filename": filename,
        "num_chunks": len(chunks),
        "num_facts": len(facts),
        "facts": facts,
    }


@app.get("/entities")
def entities():
    # Placeholder — will return extracted characters/facts later.
    return {"message": "not implemented yet"}
