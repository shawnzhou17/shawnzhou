import { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import DocumentUpload from './components/DocumentUpload'
import Sidebar from './components/Sidebar'
import { Brain } from 'lucide-react'

export default function App() {
  const [documents, setDocuments] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const handleDocumentUploaded = (doc) => {
    setDocuments((prev) => [doc, ...prev])
  }

  const handleNewConversation = () => {
    setConversationId(null)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      {/* Sidebar */}
      {sidebarOpen && (
        <Sidebar
          documents={documents}
          setDocuments={setDocuments}
          onNewConversation={handleNewConversation}
          onDocumentUploaded={handleDocumentUploaded}
          onClose={() => setSidebarOpen(false)}
        />
      )}

      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="flex items-center gap-3 px-5 py-3 border-b border-gray-800 bg-gray-900 shrink-0">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition"
              title="Open sidebar"
            >
              ☰
            </button>
          )}
          <Brain className="text-blue-400" size={24} />
          <h1 className="text-lg font-semibold tracking-tight">AskShawn‑AI</h1>
          <span className="ml-auto text-xs text-gray-500">
            RAG · pgvector · GPT‑4o mini
          </span>
        </header>

        <ChatInterface
          conversationId={conversationId}
          setConversationId={setConversationId}
        />
      </div>
    </div>
  )
}
