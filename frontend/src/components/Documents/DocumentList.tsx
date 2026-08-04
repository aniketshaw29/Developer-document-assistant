import { FileText, Trash2 } from 'lucide-react'
import type { DocumentMeta } from '../../types'

interface DocumentListProps {
  documents: DocumentMeta[]
  onDelete: (id: string) => void
}

/** Source-type badge styling for each document. */
const TYPE_STYLES: Record<string, string> = {
  github: 'bg-purple-100 text-purple-700',
  openapi: 'bg-green-100 text-green-700',
  upload: 'bg-blue-100 text-blue-700',
}

/**
 * Sidebar list of indexed documents with per-document delete buttons.
 */
export default function DocumentList({ documents, onDelete }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <p className="text-xs text-slate-400">
        No documents indexed yet. Use the upload panel above.
      </p>
    )
  }

  return (
    <ul className="space-y-2">
      {documents.map((doc) => (
        <li
          key={doc.id}
          className="group rounded-lg border border-slate-200 bg-white p-2"
        >
          <div className="flex items-start justify-between gap-1">
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-slate-700">
                {doc.title}
              </p>
              <p className="mt-0.5 text-[11px] text-slate-400">
                {doc.chunks_created} chunks · {doc.files_indexed} files
              </p>
            </div>
            <button
              type="button"
              onClick={() => onDelete(doc.id)}
              aria-label={`Delete ${doc.title}`}
              className="rounded p-1 text-slate-300 opacity-0 transition group-hover:opacity-100 hover:bg-red-50 hover:text-red-500"
            >
              <Trash2 size={12} />
            </button>
          </div>
          <span
            className={`mt-1.5 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${TYPE_STYLES[doc.source_type] ?? 'bg-slate-100 text-slate-600'}`}
          >
            <FileText size={9} />
            {doc.source_type}
          </span>
        </li>
      ))}
    </ul>
  )
}
