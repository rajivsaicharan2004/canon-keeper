import { useMemo, useState } from "react";
import "./App.css";

type UploadResponse = {
  filename: string;
  original_filename?: string;
  size_bytes?: number;
};

type Conflict = {
  entity?: string;
  attribute?: string;
  old_value?: string;
  new_value?: string;
  value_1?: string;
  value_2?: string;
  old_scene?: number | string;
  new_scene?: number | string;
  scene_1?: number | string;
  scene_2?: number | string;
  old_quote?: string;
  new_quote?: string;
  quote_1?: string;
  quote_2?: string;
  explanation?: string;
  severity?: string;
};

type AnalyzeResponse = {
  filename?: string;
  facts_count?: number;
  contradictions?: Conflict[];
  conflicts?: Conflict[];
  message?: string;
};

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const SAMPLE_STORY = `Scene 1:
Elena entered the old observatory with green eyes shining under the moonlight. She carried a silver compass given to her by her brother Marcus.

Scene 2:
Marcus warned Elena never to open the north door. The compass always pointed toward the sea.

Scene 3:
Elena returned to the observatory at dawn. Her blue eyes scanned the room as she searched for the missing compass.

Scene 4:
The compass, now described as brass, pointed toward the mountains instead of the sea.`;

function normalizeConflicts(data: AnalyzeResponse): Conflict[] {
  return data.contradictions || data.conflicts || [];
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [sampleText, setSampleText] = useState(SAMPLE_STORY);
  const [mode, setMode] = useState<"upload" | "sample">("sample");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState("");

  const conflicts = useMemo(() => {
    if (!result) return [];
    return normalizeConflicts(result);
  }, [result]);

  async function uploadAndAnalyze(targetFile: File) {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", targetFile);

      const uploadRes = await fetch(`${API}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) {
        throw new Error("Upload failed. Make sure your backend is running.");
      }

      const uploadData: UploadResponse = await uploadRes.json();
      console.log("UPLOAD RESPONSE:", uploadData);

      console.log("CALLING ANALYZE WITH:", uploadData.filename);
      const analyzeRes = await fetch(
        `${API}/analyze?filename=${encodeURIComponent(uploadData.filename)}`,
        { method: "POST" }
      );

      if (!analyzeRes.ok) {
        throw new Error("Analysis failed. Check your backend terminal.");
      }

      const analyzeData: AnalyzeResponse = await analyzeRes.json();
      setResult(analyzeData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function analyzeUploadedFile() {
    if (!file) {
      setError("Choose a manuscript file first.");
      return;
    }

    uploadAndAnalyze(file);
  }

  function analyzeSampleStory() {
    const blob = new Blob([sampleText], { type: "text/plain" });
    const sampleFile = new File([blob], "sample-story.txt", {
      type: "text/plain",
    });

    uploadAndAnalyze(sampleFile);
  }

  return (
    <main className="app">
      <nav className="nav">
        <a className="brand" href="#">
          <span className="brand-mark">CK</span>
          <span>CanonKeeper</span>
        </a>

        <div className="nav-links">
          <a href="#demo">Demo</a>
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
        </div>

        <a className="nav-cta" href="#demo">
          Try it free
        </a>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <div className="pill">Built for fiction writers</div>

          <h1>
            Catch story mistakes before your readers do.
          </h1>

          <p>
            CanonKeeper reads your scenes, remembers your canon, and flags
            contradictions in characters, objects, locations, and timelines.
          </p>

          <div className="hero-actions">
            <a href="#demo" className="primary-btn">
              Check a sample story
            </a>
            <a href="#features" className="secondary-btn">
              See how it works
            </a>
          </div>

          <div className="trust-row">
            <span>No signup needed</span>
            <span>Local Qwen support</span>
            <span>Writer-first workflow</span>
          </div>
        </div>

        <div className="hero-card">
          <div className="editor-window">
            <div className="window-bar">
              <span />
              <span />
              <span />
            </div>

            <div className="editor-layout">
              <aside className="story-sidebar">
                <p>Story Bible</p>
                <button className="active">Characters</button>
                <button>Objects</button>
                <button>Places</button>
                <button>Timeline</button>
              </aside>

              <section className="document-preview">
                <p className="chapter-label">Chapter 4</p>
                <h3>The Observatory</h3>
                <p>
                  Elena returned at dawn. Her <mark>blue eyes</mark> scanned the
                  room, searching for the missing compass.
                </p>

                <div className="inline-alert">
                  <strong>Continuity issue</strong>
                  <span>
                    Earlier scene says Elena has green eyes.
                  </span>
                </div>
              </section>
            </div>
          </div>

          <div className="floating-note note-one">
            <small>Scene 1</small>
            Elena — eye color: green
          </div>

          <div className="floating-note note-two">
            <small>Scene 4</small>
            Elena — eye color: blue
          </div>
        </div>
      </section>

      <section className="feature-strip" id="features">
        <div>
          <h2>Not another chatbot.</h2>
          <p>
            CanonKeeper is designed for continuity: it extracts facts, stores
            story memory, and compares new scenes against existing canon.
          </p>
        </div>

        <div className="mini-features">
          <article>
            <span>01</span>
            <h3>Character memory</h3>
            <p>Track traits, relationships, roles, and descriptions.</p>
          </article>

          <article>
            <span>02</span>
            <h3>Timeline checks</h3>
            <p>Catch events that happen out of order or contradict dates.</p>
          </article>

          <article>
            <span>03</span>
            <h3>Object consistency</h3>
            <p>Notice when important items change color, material, or location.</p>
          </article>
        </div>
      </section>

      <section className="demo-section" id="demo">
        <div className="section-heading">
          <div className="pill">Live analyzer</div>
          <h2>Try CanonKeeper on a sample scene.</h2>
          <p>
            Use the sample story or upload your own draft. The app will extract
            canon facts and return possible contradictions.
          </p>
        </div>

        <div className="demo-grid">
          <div className="input-card">
            <div className="mode-toggle">
              <button
                className={mode === "sample" ? "active" : ""}
                onClick={() => setMode("sample")}
              >
                Sample story
              </button>
              <button
                className={mode === "upload" ? "active" : ""}
                onClick={() => setMode("upload")}
              >
                Upload file
              </button>
            </div>

            {mode === "sample" ? (
              <>
                <textarea
                  value={sampleText}
                  onChange={(event) => setSampleText(event.target.value)}
                />

                <button
                  className="run-btn"
                  disabled={loading}
                  onClick={analyzeSampleStory}
                >
                  {loading ? "Checking canon..." : "Analyze sample story"}
                </button>
              </>
            ) : (
              <>
                <label className="upload-box">
                  <input
                    type="file"
                    accept=".txt,.md,.pdf,.docx"
                    onChange={(event) => {
                      setFile(event.target.files?.[0] || null);
                      setError("");
                      setResult(null);
                    }}
                  />

                  <span>＋</span>
                  <strong>
                    {file ? file.name : "Choose your manuscript file"}
                  </strong>
                  <small>TXT, MD, PDF, or DOCX if supported by backend</small>
                </label>

                <button
                  className="run-btn"
                  disabled={loading}
                  onClick={analyzeUploadedFile}
                >
                  {loading ? "Checking canon..." : "Analyze manuscript"}
                </button>
              </>
            )}

            {error && <div className="error">{error}</div>}
          </div>

          <div className="result-card">
            {!result && !loading && (
              <div className="empty">
                <span>✦</span>
                <h3>Your canon report will appear here.</h3>
                <p>
                  CanonKeeper will show extracted facts, conflicts, source
                  scenes, and explanations.
                </p>
              </div>
            )}

            {loading && (
              <div className="loading">
                <div className="loader" />
                <h3>Reading your story...</h3>
                <p>
                  Extracting facts, searching memory, and judging contradictions.
                </p>
              </div>
            )}

            {result && !loading && (
              <>
                <div className="report-summary">
                  <div>
                    <strong>{result.facts_count ?? "—"}</strong>
                    <span>Facts found</span>
                  </div>
                  <div>
                    <strong>{conflicts.length}</strong>
                    <span>Conflicts</span>
                  </div>
                </div>

                {conflicts.length === 0 ? (
                  <div className="clean-report">
                    <h3>No major contradictions found.</h3>
                    <p>Your story looks consistent based on this scan.</p>
                  </div>
                ) : (
                  <div className="conflict-list">
                    {conflicts.map((conflict, index) => (
                      <article className="conflict" key={index}>
                        <div className="conflict-header">
                          <span>{conflict.severity || "medium"}</span>
                          <small>Issue {index + 1}</small>
                        </div>

                        <h3>
                          {conflict.entity || "Unknown entity"}
                          {conflict.attribute
                            ? ` — ${conflict.attribute}`
                            : ""}
                        </h3>

                        <div className="comparison">
                          <div>
                            <small>
                              Scene {conflict.old_scene || conflict.scene_1 || "unknown"}
                            </small>
                            <strong>
                              {conflict.old_value || conflict.value_1 || "Previous value"}
                            </strong>
                            <p>
                              “
                              {conflict.old_quote || conflict.quote_1 || "No source quote returned."}
                              ”
                            </p>
                          </div>

                          <div>
                            <small>
                              Scene {conflict.new_scene || conflict.scene_2 || "unknown"}
                            </small>
                            <strong>
                              {conflict.new_value || conflict.value_2 || "New value"}
                            </strong>
                            <p>
                              “
                              {conflict.new_quote || conflict.quote_2 || "No source quote returned."}
                              ”
                            </p>
                          </div>
                        </div>

                        <p className="explanation">
                          {conflict.explanation ||
                            "These facts appear to describe the same story element with inconsistent details."}
                        </p>
                      </article>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </section>

      <section className="how-section" id="how">
        <div className="section-heading">
          <div className="pill">Pipeline</div>
          <h2>How CanonKeeper works</h2>
        </div>

        <div className="steps">
          <article>
            <span>1</span>
            <h3>Read</h3>
            <p>Qwen reads the uploaded scenes and identifies canon details.</p>
          </article>

          <article>
            <span>2</span>
            <h3>Remember</h3>
            <p>Facts are embedded and stored in Qdrant as story memory.</p>
          </article>

          <article>
            <span>3</span>
            <h3>Compare</h3>
            <p>New facts are matched against earlier related facts.</p>
          </article>

          <article>
            <span>4</span>
            <h3>Explain</h3>
            <p>The app explains what changed and where it happened.</p>
          </article>
        </div>
      </section>
    </main>
  );
}

export default App;
