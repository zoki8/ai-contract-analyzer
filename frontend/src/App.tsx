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
    <>
      <h1>Contract Analyzer</h1>
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button disabled={!file} onClick={handleUpload}>Analyze</button>
      {uploadError && <p>Error: {uploadError}</p>}
      {file && <p>{file.name}</p>}
      {jobId && <p>Job: {jobId}</p>}
      {job?.status === "running" && <p>Analyzing {job.done}/{job.total}</p>}

      {job?.status === "done" && job.result?.map((f, i)=> (
        <div key={i}>
          <strong>{f.category} ({f.severity})</strong>
          <blockquote>{f.quote}</blockquote>
          <p>{f.explanation}</p>
          {f.hallucinated && <p>⚠ Quote not found in contract</p>}
        </div>
      ))}
      {job?.status === "error" && <p> Error: {job.error}</p>}
    </>
  )
}

export default App