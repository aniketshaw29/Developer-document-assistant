import { useCallback, useEffect, useState } from 'react'
import type { DocumentMeta } from '../types'
import {
  deleteDocument,
  indexGithub,
  indexOpenApi,
  listDocuments,
  reindexDocument,
  uploadFiles,
} from '../lib/api'

/**
 * Document state management: listing, indexing (upload / github / openapi),
 * re-indexing, and deletion. Keeps the sidebar in sync with the backend.
 */
export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([])
  const [isIndexing, setIsIndexing] = useState(false)
  const [reindexingId, setReindexingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  /** Reload the document list from the backend. */
  const refresh = useCallback(async () => {
    try {
      const res = await listDocuments()
      setDocuments(res.documents)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [])

  // Load documents once on mount.
  useEffect(() => {
    refresh()
  }, [refresh])

  /** Wrap an indexing operation with loading/error handling, then refresh. */
  async function withIndexing(action: () => Promise<DocumentMeta>) {
    setIsIndexing(true)
    setError(null)
    try {
      await action()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsIndexing(false)
    }
  }

  const addFiles = (files: File[]) => withIndexing(() => uploadFiles(files))
  const addGithubRepo = (repoUrl: string) => withIndexing(() => indexGithub(repoUrl))
  const addOpenApiSpec = (specUrl: string) => withIndexing(() => indexOpenApi(specUrl))

  /** Re-index a single document (github/openapi only) from its stored URL. */
  const reindex = async (id: string) => {
    setReindexingId(id)
    setError(null)
    try {
      await reindexDocument(id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setReindexingId(null)
    }
  }

  const removeDocument = async (id: string) => {
    try {
      await deleteDocument(id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return {
    documents,
    isIndexing,
    reindexingId,
    error,
    refresh,
    addFiles,
    addGithubRepo,
    addOpenApiSpec,
    reindex,
    removeDocument,
  }
}
