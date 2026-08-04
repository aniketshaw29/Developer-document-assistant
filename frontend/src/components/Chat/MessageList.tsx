import { useEffect, useRef } from 'react'
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
        <div className="text-center">
          <p className="text-lg font-medium text-slate-500">
            Ask a question about your documentation
          </p>
          <p className="mt-1 text-sm">
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
      <div ref={bottomRef} />
    </div>
  )
}
