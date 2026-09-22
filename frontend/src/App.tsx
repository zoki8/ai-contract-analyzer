import { useState, useRef } from "react";
import "./App.css";

const API = "http://localhost:8000";

type Finding = {
  category: string;
  severity: "low" | "medium" | "high";
  quote: string;
  explanation: string;
  hallucinated: boolean;
};

type Job =
  | { status: "queued" | "running"; done: number; total: number }
  | { status: "done"; done: number; total: number; result: { findings: Finding[]; disclaimer: string } }
  | { status: "error"; error: string };

function severityColor(s: string) {
  if (s === "high") return "#d9534f";
  if (s === "medium") return "#f0ad4e";
  return "#5cb85c";
}

export default function App() {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const pollRef = useRef<number | null>(null);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function pollJob(jobId: string) {
    pollRef.current = window.setInterval(async () => {
      const res = await fetch(`${API}/jobs/${jobId}`);
      const data: Job = await res.json();
      setJob(data);
      if (data.status === "done" || data.status === "error") {
        stopPolling();
      }
    }, 1500);
  }

  async function handleUpload() {
    const file = fileInput.current?.files?.[0];
    if (!file) return;
    setError(null);
    setJob(null);
    stopPolling();

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${API}/analyze-contract`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const body = await res.json();
        setError(body.detail || "Upload failed.");
        return;
      }
      const { job_id } = await res.json();
      setJob({ status: "queued", done: 0, total: 0 });
      pollJob(job_id);
    } catch {
      setError("Could not reach the backend. Is it running?");
    }
  }

  return (
    <div className="container">
      <h1>AI Contract Analyzer</h1>
      <p className="disclaimer">Automated analysis. Not legal advice.</p>

      <div className="upload-box">
        <input type="file" accept="application/pdf" ref={fileInput} />
        <button onClick={handleUpload}>Analyze contract</button>
      </div>

      {error && <p className="error">{error}</p>}

      {job && (job.status === "queued" || job.status === "running") && (
        <div className="progress">
          <p>Analyzing... {job.total > 0 ? `${job.done}/${job.total} sections` : "starting..."}</p>
          <div className="bar">
            <div
              className="bar-fill"
              style={{ width: job.total > 0 ? `${(job.done / job.total) * 100}%` : "5%" }}
            />
          </div>
        </div>
      )}

      {job && job.status === "error" && <p className="error">{job.error}</p>}

      {job && job.status === "done" && (
        <div className="findings">
          <h2>Findings ({job.result.findings.length})</h2>
          {job.result.findings.length === 0 && <p>No risky clauses found.</p>}
          {job.result.findings.map((f, i) => (
            <div className="card" key={i}>
              <div className="card-header">
                <span className="category">{f.category.replace("_", " ")}</span>
                <span className="severity" style={{ backgroundColor: severityColor(f.severity) }}>
                  {f.severity}
                </span>
              </div>
              <blockquote>"{f.quote}"</blockquote>
              <p>{f.explanation}</p>
              {f.hallucinated && <p className="warn">⚠ Quote could not be verified against the source text.</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
