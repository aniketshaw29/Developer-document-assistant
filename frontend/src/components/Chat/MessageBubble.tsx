import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { BookOpen } from 'lucide-react'
import type { Message } from '../../types'
import CodeBlock from './CodeBlock'

interface MessageBubbleProps {
  message: Message
}

/**
 * A single chat message. User messages are right-aligned; assistant
 * messages are left-aligned with markdown rendering (including syntax
 * highlighted code blocks) and a collapsible citations panel.
 */
export default function MessageBubble({ message }: MessageBubbleProps) {
  const [showSources, setShowSources] = useState(false)

  const isUser = message.role === 'user'

  // While the first tokens are still pending, MessageList shows a skeleton
  // instead of an empty bubble.
  if (!isUser && message.isStreaming && message.content === '') {
    return null
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            <div className="prose prose-sm max-w-none text-slate-700 dark:prose-invert dark:text-slate-300">
              <ReactMarkdown
                components={{
                  // Route fenced code blocks through our highlighted component.
                  pre: (props) => <CodeBlock>{props.children}</CodeBlock>,
                }}
              >
                {message.content}
              </ReactMarkdown>
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
              <div className="mt-3 border-t border-slate-100 pt-2 dark:border-slate-700">
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
                        className="rounded border border-slate-100 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-800"
                      >
                        <p className="truncate font-mono text-[11px] text-slate-500 dark:text-slate-400">
                          {source.file_path}
                        </p>
                        <p className="mt-0.5 line-clamp-2 text-xs text-slate-600 dark:text-slate-300">
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
