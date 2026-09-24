import { useState } from 'react'

type Finding = {
  category:string,
  severity:string,
  quote:string,
  explanation:string,
  hallucinated:boolean
}

type Job = {
  status: string
  done?: number
  total?: number
  result?: Finding[]
  error?: string
}

function severityColor(s: string): string {
  if (s === "high") {
    return "#e74c3c"
  } else if (s === "medium") {
    return "#f39c12"
  } else if (s === "low") {
    return "#27ae60"
  } else {
    return "#ccc"
  }
}

function App() {
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<Job | null>(null)

  function pollJob(id: string) {
    const timer = setInterval(async () => {
      const res = await fetch("http://localhost:8000/jobs/" + id)
      const data: Job = await res.json()
      setJob(data)
      if (data.status === "done" || data.status === "error") {
        clearInterval(timer)
      }
    }, 1500)
  }

  async function handleUpload() {
    if (!file) return
    setUploadError(null)
    setJob(null)
    setJobId(null)

    const form = new FormData()
    form.append("file", file)
    const res = await fetch("http://localhost:8000/analyze-contract", {
      method: "POST",
      body: form,
    })
    const data = await res.json()

    if (!res.ok) {
      setUploadError(data.detail)
      return
    }

    setJobId(data.job_id)
    pollJob(data.job_id)
  }

  return (
    <div className="container">
      <h1>Contract Analyzer</h1>
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button disabled={!file} onClick={handleUpload}>Analyze</button>
      {uploadError && <p className="error">Error: {uploadError}</p>}
      {file && <p>{file.name}</p>}
      {jobId && <p>Job: {jobId}</p>}
      {job?.status === "running" && (
        <div>
          <p>Analyzing {job.done}/{job.total} sections...</p>
          <div className="progress">
            <div
              className="progress-bar"
              style={{ width: `${job.total ? (job.done! / job.total) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}

      {job?.status === "done" && job.result?.map((f, i)=> (
        <div className="card" key={i} style={{ borderLeftColor: severityColor(f.severity) }}>
          <strong>{f.category} ({f.severity})</strong>
          <blockquote>{f.quote}</blockquote>
          <p>{f.explanation}</p>
          {f.hallucinated && <p className="warning">⚠ Quote not found in contract</p>}
        </div>
      ))}
      {job?.status === "error" && <p className="error"> Error: {job.error}</p>}
    </div>
  )
}

export default App