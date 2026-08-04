import { useEffect, useState } from 'react'
import type { DocumentMeta, ProviderInfo } from './types'
import { listDocuments, listProviders } from './lib/api'

/**
 * Root application component.
 * Phase 1: renders the layout with a document sidebar and chat window.
 */
function App() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([])
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [error, setError] = useState<string | null>(null)

  // Load documents + providers once on mount.
  useEffect(() => {
    Promise.all([listDocuments(), listProviders()])
      .then(([docsRes, provRes]) => {
        setDocuments(docsRes.documents)
        setProviders(provRes.providers)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : String(e))
      })
  }, [])

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800">
      <aside className="w-80 shrink-0 border-r border-slate-200 bg-white p-4">
        <h1 className="mb-4 text-lg font-semibold">Developer Docs Assistant</h1>
        {error && (
          <p className="mb-2 rounded bg-red-50 p-2 text-sm text-red-600">
            {error}
          </p>
        )}
        <h2 className="mb-2 text-sm font-medium text-slate-500">
          Indexed documents ({documents.length})
        </h2>
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li key={doc.id} className="rounded border border-slate-200 p-2 text-sm">
              <p className="font-medium">{doc.title}</p>
              <p className="text-xs text-slate-500">
                {doc.source_type} · {doc.chunks_created} chunks
              </p>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex flex-1 flex-col">
        <div className="flex flex-1 items-center justify-center text-slate-400">
          <div className="text-center">
            <p className="text-lg font-medium">
              Ask questions about your documentation
            </p>
            <p className="mt-1 text-sm">
              Upload files or index a repo, then chat below. (UI coming in Step 5.)
            </p>
            {providers.length > 0 && (
              <p className="mt-2 text-xs text-slate-500">
                Providers: {providers.map((p) => p.name).join(', ')}
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
