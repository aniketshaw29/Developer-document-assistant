import { useRef, useState } from 'react'
import type { Message, Source, StreamEvent } from '../types'
import { getConversation, streamChat } from '../lib/api'

/**
 * Chat state management: message history, streaming, provider selection,
 * and conversation loading (for the history sidebar).
 */
export function useChat(onConversationChange?: () => void) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const [model, setModel] = useState<string | undefined>(undefined)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const conversationIdRef = useRef<string | null>(null)
  // Counter used to give each message a stable client-side id.
  const idRef = useRef(0)

  const nextId = () => `msg_${++idRef.current}`

  /** Persist the conversation id (state + ref) and refresh the sidebar. */
  function adoptConversation(id: string) {
    conversationIdRef.current = id
    setConversationId(id)
    onConversationChange?.()
  }

  /** Send a message and stream the assistant reply into the message list. */
  async function sendMessage(query: string) {
    if (!query.trim() || isStreaming) return

    // Append the user message immediately.
    const userMessage: Message = { id: nextId(), role: 'user', content: query }
    const assistantMessage: Message = {
      id: nextId(),
      role: 'assistant',
      content: '',
      isStreaming: true,
    }
    setMessages((prev) => [...prev, userMessage, assistantMessage])
    setIsStreaming(true)

    try {
      await streamChat(
        {
          query,
          provider,
          model,
          conversation_id: conversationIdRef.current ?? undefined,
        },
        (event: StreamEvent) => {
          if (event.type === 'token') {
            // Accumulate streamed tokens onto the assistant message.
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessage.id
                  ? { ...m, content: m.content + event.content }
                  : m,
              ),
            )
          } else if (event.type === 'sources' && event.sources) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessage.id ? { ...m, sources: event.sources } : m,
              ),
            )
          } else if (event.type === 'done' && event.conversation_id) {
            adoptConversation(event.conversation_id)
          } else if (event.type === 'error') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessage.id
                  ? { ...m, error: event.content, isStreaming: false }
                  : m,
              ),
            )
          }
        },
      )
    } catch (err) {
      // Network / non-SSE errors surface here.
      const message = err instanceof Error ? err.message : String(err)
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessage.id ? { ...m, error: message, isStreaming: false } : m,
        ),
      )
    } finally {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessage.id ? { ...m, isStreaming: false } : m,
        ),
      )
      setIsStreaming(false)
    }
  }

  /** Clear all messages and start a fresh conversation. */
  function resetConversation() {
    conversationIdRef.current = null
    setConversationId(null)
    setMessages([])
    onConversationChange?.()
  }

  /** Load a past conversation from the backend and resume it. */
  async function loadConversation(id: string) {
    const detail = await getConversation(id)
    conversationIdRef.current = id
    setConversationId(id)
    setMessages(
      detail.messages.map((m, i) => ({
        id: `hist_${id}_${i}`,
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
      })),
    )
  }

  /**
   * Set provider + model from a single encoded dropdown value
   * (format: "provider::model", or "" for auto).
   */
  function selectOption(encoded: string) {
    if (!encoded) {
      setProvider(undefined)
      setModel(undefined)
      return
    }
    const [providerName, modelName] = encoded.split('::')
    setProvider(providerName)
    setModel(modelName)
  }

  /** Attach sources to a message (used for the non-streaming path). */
  function attachSources(messageId: string, sources: Source[]) {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, sources } : m)),
    )
  }

  return {
    messages,
    isStreaming,
    provider,
    setProvider,
    model,
    setModel,
    conversationId,
    selectOption,
    sendMessage,
    resetConversation,
    loadConversation,
    attachSources,
  }
}
