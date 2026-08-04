import { useState } from 'react'
import { Send } from 'lucide-react'

interface ComposerProps {
  onSend: (query: string) => void
  disabled: boolean
}

/**
 * Message input area. Enter sends, Shift+Enter adds a newline.
 * Disabled while a response is streaming.
 */
export default function Composer({ onSend, disabled }: ComposerProps) {
  const [value, setValue] = useState('')

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  return (
    <div className="border-t border-slate-200 bg-white p-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            // Enter sends unless Shift is held (newline).
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder="Ask about your indexed documentation…"
          rows={1}
          className="max-h-40 min-h-[2.5rem] flex-1 resize-y rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm outline-none focus:border-blue-400 focus:bg-white focus:ring-1 focus:ring-blue-200"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
