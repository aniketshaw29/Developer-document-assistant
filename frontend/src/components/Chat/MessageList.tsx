import { useEffect, useRef } from 'react'
import { MessageSquareText } from 'lucide-react'
import type { Message } from '../../types'
import MessageBubble from './MessageBubble'

interface MessageListProps {
  messages: Message[]
}

/**
 * Scrollable list of chat messages. Auto-scrolls to the bottom whenever
 * new content arrives (i.e. while streaming).
 */
export default function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-slate-400">
        <div className="px-6 text-center">
          {/* Empty-state illustration */}
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-500 dark:bg-blue-950 dark:text-blue-400">
            <MessageSquareText size={28} />
          </div>
          <p className="text-lg font-medium text-slate-500 dark:text-slate-300">
            Ask a question about your documentation
          </p>
          <p className="mt-1 text-sm text-slate-400">
            e.g. "How do I configure Kafka retry?" or "Which endpoint creates orders?"
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {/* Loading skeleton while waiting for the first token of a reply. */}
      {messages.some((m) => m.isStreaming && m.content === '') && (
        <div className="flex justify-start">
          <div className="w-2/3 space-y-2 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <div className="h-3 w-full animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            <div className="h-3 w-4/5 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            <div className="h-3 w-3/5 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
