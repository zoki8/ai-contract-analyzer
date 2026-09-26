import { useEffect, useRef, useState } from 'react'

const API = 'http://localhost:8000'
const POLL_MS = 1500
const MAX_MB = 10

type Severity = 'low' | 'medium' | 'high'

type Finding = {
  category: string
  severity: Severity
  quote: string
  explanation: string
  hallucinated: boolean
}

type Job = {
  status: 'queued' | 'running' | 'done' | 'error'
  done?: number
  total?: number
  result?: Finding[]
  error?: string
}

const CATEGORY_LABELS: Record<string, string> = {
  penalty: 'Penalty',
  payment_terms: 'Payment terms',
  auto_renewal: 'Automatic renewal',
  termination: 'Termination',
  liability: 'Limited liability',
  other: 'Other risk',
}

const SEVERITIES: Severity[] = ['high', 'medium', 'low']

const SEVERITY_LABELS: Record<Severity, string> = {
  high: 'High risk',
  medium: 'Medium risk',
  low: 'Low risk',
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function isPdf(f: File): boolean {
  return f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
}

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | null>(null)

  function stopPolling() {
    if (timer.current !== null) {
      clearInterval(timer.current)
      timer.current = null
    }
  }

  // stop polling if the component is removed from the page
  useEffect(() => stopPolling, [])

  function pickFile(f: File | undefined) {
    if (!f) return
    if (!isPdf(f)) {
      setError('That file is not a PDF. Choose a contract saved as PDF.')
      return
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`The file is ${formatSize(f.size)}. The limit is ${MAX_MB} MB.`)
      return
    }
    setFile(f)
    setError(null)
    setJob(null)
  }

  function poll(id: string) {
    timer.current = window.setInterval(async () => {
      try {
        const res = await fetch(`${API}/jobs/${id}`)
        if (!res.ok) throw new Error(`status ${res.status}`)
        const data: Job = await res.json()
        setJob(data)
        if (data.status === 'done' || data.status === 'error') stopPolling()
      } catch {
        stopPolling()
        setJob(null)
        setError('Lost the connection to the analysis server. Check that the backend is still running, then try again.')
      }
    }, POLL_MS)
  }

  async function analyze() {
    if (!file) return
    stopPolling()
    setError(null)
    setJob({ status: 'queued' })

    const form = new FormData()
    form.append('file', file)

    let res: Response
    try {
      res = await fetch(`${API}/analyze-contract`, { method: 'POST', body: form })
    } catch {
      setJob(null)
      setError("Can't reach the analysis server. Start the backend on port 8000 and try again.")
      return
    }

    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      setJob(null)
      setError(data.detail ?? `The upload failed (status ${res.status}).`)
      return
    }
    poll(data.job_id)
  }

  function reset() {
    stopPolling()
    setFile(null)
    setJob(null)
    setError(null)
  }

  const busy = job?.status === 'queued' || job?.status === 'running'
  const finished = job?.status === 'done'
  const message = error ?? (job?.status === 'error' ? job.error ?? 'The analysis failed.' : null)

  const findings = [...(job?.result ?? [])].sort(
    (a, b) => SEVERITIES.indexOf(a.severity) - SEVERITIES.indexOf(b.severity),
  )
  const counts = SEVERITIES.map((s) => ({
    severity: s,
    count: findings.filter((f) => f.severity === s).length,
  })).filter((c) => c.count > 0)

  const done = job?.done ?? 0
  const total = job?.total ?? 0
  const percent = total ? (done / total) * 100 : 0

  return (
    <main className="page">
      <div className="aurora" aria-hidden="true" />

      <header className="masthead">
        <span className="chip">Runs locally. Your contract never leaves this computer.</span>
        <h1>Contract Analyzer</h1>
        <p className="lede">
          Upload a contract and see which clauses deserve a closer read before you sign:
          penalties, payment terms, automatic renewal, termination and limits on liability.
        </p>
      </header>

      {!finished && (
        <section className="upload glass" aria-label="Upload a contract">
          <label
            className={`dropzone${dragging ? ' is-dragging' : ''}${file ? ' has-file' : ''}${busy ? ' is-busy' : ''}`}
            onDragOver={(e) => {
              e.preventDefault()
              if (!busy) setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              if (!busy) pickFile(e.dataTransfer.files[0])
            }}
          >
            <input
              type="file"
              accept="application/pdf"
              className="visually-hidden"
              disabled={busy}
              onChange={(e) => {
                pickFile(e.target.files?.[0])
                e.target.value = ''
              }}
            />
            <span className="file-icon" aria-hidden="true">PDF</span>
            {file ? (
              <>
                <span className="dropzone-title">{file.name}</span>
                <span className="dropzone-hint">
                  {formatSize(file.size)}. {busy ? 'Being analyzed.' : 'Click or drop to choose a different file.'}
                </span>
              </>
            ) : (
              <>
                <span className="dropzone-title">Drop a contract PDF here</span>
                <span className="dropzone-hint">or click to choose a file, up to {MAX_MB} MB</span>
              </>
            )}
          </label>

          <button className="button primary" onClick={analyze} disabled={!file || busy}>
            {busy ? 'Analyzing…' : 'Analyze contract'}
          </button>

          {busy && (
            <div className="progress" role="status">
              <p>
                {total
                  ? `Reading section ${Math.min(done + 1, total)} of ${total}`
                  : 'Preparing the contract'}
              </p>
              <div className="bar">
                <div className="bar-fill" style={{ width: `${Math.max(percent, 4)}%` }} />
              </div>
            </div>
          )}
        </section>
      )}

      {message && (
        <p className="error glass" role="alert">
          {message}
        </p>
      )}

      {finished && (
        <section className="results" aria-label="Analysis results">
          <div className="summary glass">
            <div className="summary-head">
              <div>
                <h2>
                  {findings.length === 0
                    ? 'No risky clauses found'
                    : `${findings.length} ${findings.length === 1 ? 'clause' : 'clauses'} to review`}
                </h2>
                {file && <p className="summary-file">{file.name}</p>}
              </div>
              <button className="button secondary" onClick={reset}>
                Analyze another contract
              </button>
            </div>

            {counts.length > 0 ? (
              <>
                <div
                  className="meter"
                  role="img"
                  aria-label={counts.map((c) => `${c.count} ${c.severity} risk`).join(', ')}
                >
                  {counts.map((c) => (
                    <span
                      key={c.severity}
                      className={`meter-segment sev-${c.severity}`}
                      style={{ flexGrow: c.count }}
                    />
                  ))}
                </div>
                <ul className="tally">
                  {counts.map((c) => (
                    <li key={c.severity}>
                      <span className={`dot sev-${c.severity}`} aria-hidden="true" />
                      {c.count} {c.severity}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="empty">
                No penalties, one-sided terms or limits on liability were flagged. Standard,
                mutual clauses are not listed.
              </p>
            )}
          </div>

          {findings.length > 0 && (
            <ul className="findings">
              {findings.map((f, i) => (
                <li key={i} className={`finding glass sev-${f.severity}`}>
                  <div className="finding-meta">
                    <span className="category">{CATEGORY_LABELS[f.category] ?? f.category}</span>
                    <span className={`pill sev-${f.severity}`}>{SEVERITY_LABELS[f.severity]}</span>
                  </div>
                  <blockquote className="quote">{f.quote}</blockquote>
                  <p className="explanation">{f.explanation}</p>
                  {f.hallucinated && (
                    <p className="warning">
                      This quote was not found word for word in the contract. Check the original
                      before relying on it.
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}

          <p className="disclaimer">Automated analysis, not legal advice.</p>
        </section>
      )}
    </main>
  )
}

export default App
