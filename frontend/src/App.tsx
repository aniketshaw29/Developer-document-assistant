import { useEffect, useState } from 'react'
import { BookMarked } from 'lucide-react'
import type { ProviderInfo } from './types'
import { listProviders } from './lib/api'
import { useDocuments } from './hooks/useDocuments'
import UploadPanel from './components/Documents/UploadPanel'
import DocumentList from './components/Documents/DocumentList'
import ChatWindow from './components/Chat/ChatWindow'

/**
 * Root application: two-column layout with a document sidebar on the left
 * and the chat window filling the rest of the screen.
 */
function App() {
  const [providers, setProviders] = useState<ProviderInfo[]>([])
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

  // Which providers are usable right now?
  const activeProviders = providers.filter((p) => p.available).map((p) => p.name)

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800">
      {/* Sidebar */}
      <aside className="flex w-80 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-4">
          <h1 className="flex items-center gap-2 text-base font-semibold">
            <BookMarked className="text-blue-600" size={18} />
            Docs Assistant
          </h1>
          <p className="mt-0.5 text-xs text-slate-400">
            ChatGPT for your codebases
          </p>
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

        <div className="border-t border-slate-200 p-3">
          <p className="text-[11px] text-slate-400">
            Provider:{' '}
            {activeProviders.length > 0 ? (
              <span className="font-medium text-slate-600">
                {activeProviders.join(', ')}
              </span>
            ) : (
              <span className="text-amber-600">
                none configured — add an API key or start Ollama
              </span>
            )}
          </p>
        </div>
      </aside>

      {/* Chat window */}
      <ChatWindow />
    </div>
  )
}

export default App
