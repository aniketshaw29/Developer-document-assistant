import { FileText, Loader2, RefreshCw, Trash2 } from 'lucide-react'
import type { DocumentMeta } from '../../types'

interface DocumentListProps {
  documents: DocumentMeta[]
  onDelete: (id: string) => void
  /** Id of the document currently being re-indexed, if any. */
  onReindex: (id: string) => void
  /** True while this document is being re-indexed (shows a spinner). */
  reindexingId?: string | null
}

/** Source-type badge styling for each document. */
const TYPE_STYLES: Record<string, string> = {
  github: 'bg-purple-100 text-purple-700',
  openapi: 'bg-green-100 text-green-700',
  upload: 'bg-blue-100 text-blue-700',
}

/**
 * Sidebar list of indexed documents with per-document re-index and
 * delete buttons. Re-index is only offered for sources that can be
 * refreshed (github / openapi), since uploads have no persistent URL.
 */
export default function DocumentList({
  documents,
  onDelete,
  onReindex,
  reindexingId = null,
}: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <p className="text-xs text-slate-400">
        No documents indexed yet. Use the upload panel above.
      </p>
    )
  }

  const canReindex = (doc: DocumentMeta) =>
    (doc.source_type === 'github' || doc.source_type === 'openapi') && !!doc.source

  return (
    <ul className="space-y-2">
      {documents.map((doc) => {
        const isReindexing = reindexingId === doc.id
        return (
          <li
            key={doc.id}
            className="group rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="flex items-start justify-between gap-1">
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-slate-700 dark:text-slate-200">
                  {doc.title}
                </p>
                <p className="mt-0.5 text-[11px] text-slate-400">
                  {doc.chunks_created} chunks · {doc.files_indexed} files
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {canReindex(doc) && (
                  <button
                    type="button"
                    onClick={() => onReindex(doc.id)}
                    disabled={isReindexing}
                    aria-label={`Re-index ${doc.title}`}
                    title={isReindexing ? 'Re-indexing…' : 'Re-index from source'}
                    className="rounded p-1 text-slate-300 opacity-0 transition group-hover:opacity-100 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-100 dark:hover:bg-blue-950"
                  >
                    {isReindexing ? (
                      <Loader2 size={12} className="animate-spin text-blue-600" />
                    ) : (
                      <RefreshCw size={12} />
                    )}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onDelete(doc.id)}
                  aria-label={`Delete ${doc.title}`}
                  className="rounded p-1 text-slate-300 opacity-0 transition group-hover:opacity-100 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
            <span
              className={`mt-1.5 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${TYPE_STYLES[doc.source_type] ?? 'bg-slate-100 text-slate-600'}`}
            >
              <FileText size={9} />
              {doc.source_type}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
