import { useState, useRef } from 'react'
import { Upload, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'

const API_BASE = '/api'

export default function DocumentUpload({ onDocumentUploaded }) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [status, setStatus] = useState(null) // { type: 'success'|'error', message }
  const inputRef = useRef(null)

  const handleFile = async (file) => {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'md', 'txt'].includes(ext)) {
      setStatus({ type: 'error', message: 'Only PDF, MD, and TXT files are supported.' })
      return
    }

    setUploading(true)
    setStatus(null)
    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: 'POST',
        body: form,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed.' }))
        throw new Error(err.detail || 'Upload failed.')
      }
      const doc = await res.json()
      setStatus({ type: 'success', message: `"${doc.filename}" uploaded — ${doc.chunk_count} chunks indexed.` })
      onDocumentUploaded?.(doc)
    } catch (err) {
      setStatus({ type: 'error', message: err.message })
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed px-4 py-5 text-center transition ${
          dragging ? 'border-blue-400 bg-blue-950/30' : 'border-gray-600 hover:border-blue-500 hover:bg-gray-800/50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.md,.txt"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {uploading ? (
          <Loader2 size={20} className="animate-spin mx-auto text-blue-400 mb-1" />
        ) : (
          <Upload size={20} className="mx-auto text-gray-500 mb-1" />
        )}
        <p className="text-xs text-gray-400">
          {uploading ? 'Uploading…' : 'Drop PDF / MD / TXT or click'}
        </p>
      </div>

      {status && (
        <div
          className={`flex items-start gap-2 rounded-lg px-3 py-2 text-xs ${
            status.type === 'success' ? 'bg-green-950/50 text-green-400' : 'bg-red-950/50 text-red-400'
          }`}
        >
          {status.type === 'success' ? <CheckCircle2 size={14} className="mt-0.5 shrink-0" /> : <AlertCircle size={14} className="mt-0.5 shrink-0" />}
          <span>{status.message}</span>
        </div>
      )}
    </div>
  )
}
