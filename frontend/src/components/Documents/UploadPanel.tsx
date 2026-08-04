import { useRef, useState } from 'react'
import { FileUp, GitBranch, Globe, Loader2 } from 'lucide-react'

interface UploadPanelProps {
  onUploadFiles: (files: File[]) => void
  onIndexGithub: (repoUrl: string) => void
  onIndexOpenApi: (specUrl: string) => void
  isIndexing: boolean
}

type Tab = 'files' | 'github' | 'openapi'

/**
 * Document ingestion panel with three tabs: file upload, GitHub repo,
 * and Swagger/OpenAPI URL.
 */
export default function UploadPanel({
  onUploadFiles,
  onIndexGithub,
  onIndexOpenApi,
  isIndexing,
}: UploadPanelProps) {
  const [tab, setTab] = useState<Tab>('files')
  const [url, setUrl] = useState('')
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFiles(files: FileList | null) {
    if (files && files.length > 0) {
      onUploadFiles(Array.from(files))
    }
  }

  function submitUrl() {
    const trimmed = url.trim()
    if (!trimmed || isIndexing) return
    if (tab === 'github') onIndexGithub(trimmed)
    else onIndexOpenApi(trimmed)
    setUrl('')
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      {/* Tabs */}
      <div className="mb-3 flex gap-1 rounded-lg bg-slate-100 p-1 text-xs">
        {(
          [
            ['files', 'Files', FileUp],
            ['github', 'GitHub', GitBranch],
            ['openapi', 'OpenAPI', Globe],
          ] as [Tab, string, typeof FileUp][]
        ).map(([key, label, Icon]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`flex flex-1 items-center justify-center gap-1 rounded-md px-2 py-1.5 font-medium transition ${
              tab === key
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Icon size={12} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'files' && (
        <>
          {/* Drag-and-drop area */}
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              handleFiles(e.dataTransfer.files)
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed py-6 text-center transition ${
              dragging
                ? 'border-blue-400 bg-blue-50'
                : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'
            }`}
          >
            <FileUp className="mb-2 text-slate-400" size={20} />
            <p className="text-xs font-medium text-slate-600">
              Drop files here or click to browse
            </p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              Markdown, PDF, code files
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </div>
        </>
      )}

      {(tab === 'github' || tab === 'openapi') && (
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitUrl()}
            placeholder={
              tab === 'github'
                ? 'https://github.com/owner/repo'
                : 'https://api.example.com/swagger.json'
            }
            className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs outline-none focus:border-blue-400 focus:bg-white"
          />
          <button
            type="button"
            onClick={submitUrl}
            disabled={isIndexing || !url.trim()}
            className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {isIndexing ? <Loader2 size={12} className="animate-spin" /> : <Globe size={12} />}
            Index
          </button>
        </div>
      )}

      {isIndexing && (
        <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-500">
          <Loader2 size={11} className="animate-spin" /> Indexing… this can take a
          minute for large repos.
        </p>
      )}
    </div>
  )
}
