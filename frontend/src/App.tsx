import { useState } from 'react'

type Job = {
  status: string
  done?: number
  total?: number
  result?: any[]
  error?: string
}

function App() {
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

    const form = new FormData()
    form.append("file", file)
    const res = await fetch("http://localhost:8000/analyze-contract", {
      method: "POST",
      body: form,
    })
    const data = await res.json()
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
      {file && <p>{file.name}</p>}
      {jobId && <p>Job: {jobId}</p>}
      {job && <p>Status: {job.status} {job.done}/{job.total}</p>}
    </>
  )
}

export default App