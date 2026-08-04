import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { BookOpen } from 'lucide-react'
import type { Message } from '../../types'

interface MessageBubbleProps {
  message: Message
}

/**
 * A single chat message. User messages are right-aligned; assistant
 * messages are left-aligned with markdown rendering and a collapsible
 * citations panel.
 */
export default function MessageBubble({ message }: MessageBubbleProps) {
  const [showSources, setShowSources] = useState(false)

  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white border border-slate-200 shadow-sm'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            <div className="prose prose-sm max-w-none text-slate-700">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>

            {message.isStreaming && (
              <span className="mt-1 inline-block animate-pulse text-slate-400">
                ▊
              </span>
            )}

            {message.error && (
              <p className="mt-2 rounded bg-red-50 p-2 text-xs text-red-600">
                {message.error}
              </p>
            )}

            {/* Citations panel */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 border-t border-slate-100 pt-2">
                <button
                  type="button"
                  onClick={() => setShowSources((v) => !v)}
                  className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
                >
                  <BookOpen size={12} />
                  {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
                  {showSources ? ' ▴' : ' ▾'}
                </button>
                {showSources && (
                  <ul className="mt-2 space-y-1.5">
                    {message.sources.map((source, i) => (
                      <li
                        key={i}
                        className="rounded border border-slate-100 bg-slate-50 p-2"
                      >
                        <p className="truncate font-mono text-[11px] text-slate-500">
                          {source.file_path}
                        </p>
                        <p className="mt-0.5 line-clamp-2 text-xs text-slate-600">
                          {source.text}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
