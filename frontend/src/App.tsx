import { useState } from 'react'

function App() {
  const [file, setFile] = useState<File | null>(null)
  return (
    <>
      <h1>Contract Analyzer</h1>
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files?.[0]??null)}
      />
      <button disabled={!file}>Analyze</button>
      {file && <p>{file.name}</p>}
      
    </>
  )
}

export default App
