import { useEffect } from 'react'
import DocumentUpload from './DocumentUpload'
import { FileText, Trash2, X, PlusCircle } from 'lucide-react'

const API_BASE = '/api'

export default function Sidebar({ documents, setDocuments, onNewConversation, onDocumentUploaded, onClose }) {
  useEffect(() => {
    fetch(`${API_BASE}/documents/`)
      .then((r) => r.json())
      .then((docs) => setDocuments(docs))
      .catch(() => {})
  }, [setDocuments])

  const deleteDocument = async (id) => {
    try {
      await fetch(`${API_BASE}/documents/${id}`, { method: 'DELETE' })
      setDocuments((prev) => prev.filter((d) => d.id !== id))
    } catch {
      // ignore
    }
  }

  return (
    <aside className="w-72 shrink-0 flex flex-col bg-gray-900 border-r border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <span className="text-sm font-semibold text-gray-200">Knowledge Base</span>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition"
          title="Close sidebar"
        >
          <X size={16} />
        </button>
      </div>

      {/* New conversation */}
      <div className="px-4 pt-4 pb-2">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm py-2 transition"
        >
          <PlusCircle size={16} />
          New Conversation
        </button>
      </div>

      {/* Upload */}
      <div className="px-4 py-3 border-b border-gray-800">
        <p className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Upload</p>
        <DocumentUpload onDocumentUploaded={onDocumentUploaded} />
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <p className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
          Documents ({documents.length})
        </p>
        {documents.length === 0 && (
          <p className="text-xs text-gray-600 italic">No documents uploaded yet.</p>
        )}
        <ul className="space-y-1">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className="flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-gray-800 group"
            >
              <FileText size={14} className="shrink-0 text-blue-400" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-200 truncate">{doc.filename}</p>
                <p className="text-[11px] text-gray-500">{doc.chunk_count} chunks</p>
              </div>
              <button
                onClick={() => deleteDocument(doc.id)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-700 text-gray-500 hover:text-red-400 transition"
                title="Delete document"
              >
                <Trash2 size={13} />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  )
}
