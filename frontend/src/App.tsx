import { useCallback, useEffect, useRef, useState } from 'react'
import { BookMarked, Moon, Sun } from 'lucide-react'
import type { ConversationSummary, ProviderInfo } from './types'
import { deleteConversation, listConversations, listProviders } from './lib/api'
import { useDocuments } from './hooks/useDocuments'
import UploadPanel from './components/Documents/UploadPanel'
import DocumentList from './components/Documents/DocumentList'
import ChatWindow, { type ChatWindowHandle } from './components/Chat/ChatWindow'
import ConversationHistory, {
  HistoryHeader,
} from './components/Chat/ConversationHistory'

/** Persisted theme preference key. */
const THEME_KEY = 'docs-assistant-theme'

function initialTheme(): boolean {
  const saved = localStorage.getItem(THEME_KEY)
  if (saved !== null) return saved === 'dark'
  // Fall back to the OS preference on first visit.
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/**
 * Root application: two-column layout with a document/conversation sidebar
 * on the left and the chat window filling the rest of the screen.
 * Toggling dark mode flips the `dark` class on <html>.
 */
function App() {
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [isDark, setIsDark] = useState(initialTheme)
  const chatRef = useRef<ChatWindowHandle>(null)

  const {
    documents,
    isIndexing,
    reindexingId,
    error,
    addFiles,
    addGithubRepo,
    addOpenApiSpec,
    reindex,
    removeDocument,
  } = useDocuments()

  // Load available providers once on mount.
  useEffect(() => {
    listProviders()
      .then((res) => setProviders(res.providers))
      .catch(() => setProviders([]))
  }, [])

  // Apply the theme class to <html> whenever it changes.
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem(THEME_KEY, isDark ? 'dark' : 'light')
  }, [isDark])

  /** Refresh the conversation sidebar from the backend. */
  const refreshConversations = useCallback(async () => {
    try {
      const res = await listConversations()
      setConversations(res.conversations)
      // Keep the active id pointing at an existing conversation.
      setActiveConversationId((current) =>
        current && res.conversations.some((c) => c.id === current) ? current : null,
      )
    } catch {
      // History is best-effort; ignore failures here.
    }
  }, [])

  // Load conversations once on mount.
  useEffect(() => {
    refreshConversations()
  }, [refreshConversations])

  /** Resume a conversation from the sidebar. */
  const selectConversation = useCallback(async (id: string) => {
    setActiveConversationId(id)
    await chatRef.current?.loadConversation(id)
  }, [])

  /** Delete a conversation and refresh the sidebar. */
  const handleDeleteConversation = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id)
      } catch {
        // Ignore deletion errors; the refresh below will show the truth.
      }
      await refreshConversations()
    },
    [refreshConversations],
  )

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-200">
      {/* Sidebar */}
      <aside className="flex w-80 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
          <div>
            <h1 className="flex items-center gap-2 text-base font-semibold">
              <BookMarked className="text-blue-600" size={18} />
              Docs Assistant
            </h1>
            <p className="mt-0.5 text-xs text-slate-400">
              ChatGPT for your codebases
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsDark((v) => !v)}
            aria-label="Toggle dark mode"
            title="Toggle dark mode"
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          <UploadPanel
            onUploadFiles={addFiles}
            onIndexGithub={addGithubRepo}
            onIndexOpenApi={addOpenApiSpec}
            isIndexing={isIndexing}
          />

          {error && (
            <p className="rounded-lg bg-red-50 p-2 text-xs text-red-600">{error}</p>
          )}

          <div>
            <HistoryHeader />
            <ConversationHistory
              conversations={conversations}
              activeId={activeConversationId}
              onSelect={selectConversation}
              onDelete={handleDeleteConversation}
            />
          </div>

          <div>
            <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              Indexed documents
            </h2>
            <DocumentList
              documents={documents}
              onDelete={removeDocument}
              onReindex={reindex}
              reindexingId={reindexingId}
            />
          </div>
        </div>

        <div className="border-t border-slate-200 p-3 dark:border-slate-800">
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-400">
            LLM providers
          </p>
          <ul className="space-y-1">
            {providers.map((p) => (
              <li key={p.name} className="flex items-center gap-2 text-[11px]">
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${
                    p.available ? 'bg-green-500' : 'bg-red-400'
                  }`}
                  title={p.available ? 'Available' : 'Not configured / offline'}
                />
                <span className="capitalize text-slate-600 dark:text-slate-400">
                  {p.name}
                </span>
                <span className="ml-auto truncate text-slate-400">
                  {p.available ? p.model : 'offline'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {/* Chat window */}
      <ChatWindow
        ref={chatRef}
        providers={providers}
        onConversationChange={refreshConversations}
      />
    </div>
  )
}

export default App
