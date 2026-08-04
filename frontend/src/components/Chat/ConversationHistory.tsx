import { History, MessageSquare, Trash2 } from 'lucide-react'
import type { ConversationSummary } from '../../types'

interface ConversationHistoryProps {
  conversations: ConversationSummary[]
  /** Id of the conversation currently shown in the chat window. */
  activeId?: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

/**
 * Sidebar list of past conversations. Clicking an entry resumes it;
 * the trash button removes it from history.
 */
export default function ConversationHistory({
  conversations,
  activeId = null,
  onSelect,
  onDelete,
}: ConversationHistoryProps) {
  if (conversations.length === 0) {
    return (
      <p className="text-xs text-slate-400">
        No past chats yet. Ask a question to get started.
      </p>
    )
  }

  return (
    <ul className="space-y-1.5">
      {conversations.map((conv) => (
        <li key={conv.id} className="group flex items-center gap-1">
          <button
            type="button"
            onClick={() => onSelect(conv.id)}
            className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs transition ${
              activeId === conv.id
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
            }`}
            title={conv.title}
          >
            <MessageSquare size={12} className="shrink-0" />
            <span className="truncate">{conv.title}</span>
          </button>
          <button
            type="button"
            onClick={() => onDelete(conv.id)}
            aria-label={`Delete conversation ${conv.title}`}
            className="rounded p-1 text-slate-300 opacity-0 transition group-hover:opacity-100 hover:bg-red-50 hover:text-red-500"
          >
            <Trash2 size={12} />
          </button>
        </li>
      ))}
    </ul>
  )
}

/** Small header used by App to label the history section. */
export function HistoryHeader() {
  return (
    <h2 className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
      <History size={11} />
      Chat history
    </h2>
  )
}
