import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { ChevronDown, ChevronUp, BookOpen } from 'lucide-react'

export default function MessageBubble({ message }) {
  const [citationsOpen, setCitationsOpen] = useState(false)
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} gap-3 max-w-3xl mx-auto w-full`}>
      {/* Avatar */}
      {!isUser && (
        <div className="shrink-0 w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold mt-1">
          AI
        </div>
      )}

      <div className={`flex flex-col gap-1.5 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble */}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : 'bg-gray-800 text-gray-100 rounded-bl-sm'
          }`}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{message.content || (message.streaming ? '▌' : '')}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations toggle */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="w-full">
            <button
              onClick={() => setCitationsOpen((o) => !o)}
              className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition"
            >
              <BookOpen size={13} />
              {message.citations.length} source{message.citations.length !== 1 ? 's' : ''}
              {citationsOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>

            {citationsOpen && (
              <div className="mt-2 space-y-2">
                {message.citations.map((c) => (
                  <div
                    key={c.source_num}
                    className="rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-xs text-gray-300"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-blue-400">
                        [Source {c.source_num}] {c.filename}
                      </span>
                      <span className="text-gray-500">
                        chunk {c.chunk_index} · {(c.similarity * 100).toFixed(1)}% match
                      </span>
                    </div>
                    <p className="italic text-gray-400 line-clamp-3">{c.excerpt}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="shrink-0 w-7 h-7 rounded-full bg-gray-600 flex items-center justify-center text-xs font-bold mt-1">
          U
        </div>
      )}
    </div>
  )
}
