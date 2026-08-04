import { forwardRef, useImperativeHandle } from 'react'
import { Menu, RotateCcw } from 'lucide-react'
import { useChat } from '../../hooks/useChat'
import type { ProviderInfo } from '../../types'
import MessageList from './MessageList'
import Composer from './Composer'

/** Imperative handle so App can load a conversation from the sidebar. */
export interface ChatWindowHandle {
  loadConversation: (id: string) => Promise<void>
}

interface ChatWindowProps {
  providers: ProviderInfo[]
  /** Fired whenever a conversation is created/updated so the sidebar refreshes. */
  onConversationChange?: () => void
  /** Opens the mobile sidebar drawer (hamburger button, md:hidden). */
  onOpenSidebar?: () => void
}

/**
 * The main chat panel: header, scrollable message list, and composer.
 * Exposes `loadConversation` through the ref for the history sidebar.
 */
const ChatWindow = forwardRef<ChatWindowHandle, ChatWindowProps>(
  function ChatWindow({ providers, onConversationChange, onOpenSidebar }, ref) {
    const {
      messages,
      isStreaming,
      provider,
      model,
      selectOption,
      sendMessage,
      resetConversation,
      loadConversation,
    } = useChat(onConversationChange)

    useImperativeHandle(ref, () => ({ loadConversation }), [loadConversation])

    return (
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 md:px-6">
          <div className="flex min-w-0 items-center gap-2">
            {onOpenSidebar && (
              <button
                type="button"
                onClick={onOpenSidebar}
                aria-label="Open sidebar"
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-300 md:hidden"
              >
                <Menu size={18} />
              </button>
            )}
            <h1 className="truncate text-sm font-semibold text-slate-700 dark:text-slate-200">
              Documentation Chat
            </h1>
          </div>
          <button
            type="button"
            onClick={resetConversation}
            disabled={messages.length === 0}
            className="flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-40 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            <RotateCcw size={12} />
            New chat
          </button>
        </div>

        <MessageList messages={messages} />
        <Composer
          onSend={sendMessage}
          disabled={isStreaming}
          providers={providers}
          provider={provider}
          model={model}
          onSelectionChange={selectOption}
        />
      </div>
    )
  },
)

export default ChatWindow
