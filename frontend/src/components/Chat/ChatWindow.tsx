import { RotateCcw } from 'lucide-react'
import { useChat } from '../../hooks/useChat'
import MessageList from './MessageList'
import Composer from './Composer'

/**
 * The main chat panel: header, scrollable message list, and composer.
 */
export default function ChatWindow() {
  const { messages, isStreaming, sendMessage, resetConversation } = useChat()

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <h1 className="text-sm font-semibold text-slate-700">
          Documentation Chat
        </h1>
        <button
          type="button"
          onClick={resetConversation}
          disabled={messages.length === 0}
          className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-40"
        >
          <RotateCcw size={12} />
          New chat
        </button>
      </div>

      <MessageList messages={messages} />
      <Composer onSend={sendMessage} disabled={isStreaming} />
    </div>
  )
}
