import { useState } from 'react'
import { Cpu, Send } from 'lucide-react'
import type { ProviderInfo } from '../../types'

interface ComposerProps {
  onSend: (query: string) => void
  disabled: boolean
  /** Providers reported by the backend (used to build the dropdown). */
  providers: ProviderInfo[]
  /** Currently selected provider name, if any. */
  provider?: string
  /** Currently selected model, if any. */
  model?: string
  /** Called when the user picks a provider+model combo (encoded value). */
  onSelectionChange: (encoded: string) => void
}

/** Encodes a provider+model pair into a single select value. */
const encodeOption = (provider: string, model: string) =>
  `${provider}::${model}`

/**
 * Message input area. Enter sends, Shift+Enter adds a newline.
 * Disabled while a response is streaming.
 */
export default function Composer({
  onSend,
  disabled,
  providers,
  provider,
  model,
  onSelectionChange,
}: ComposerProps) {
  const [value, setValue] = useState('')

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  const available = providers.filter((p) => p.available)
  // Flatten provider+model pairs into one option list with optgroups.
  const optionGroups = available.map((p) => ({
    name: p.name,
    models:
      p.models && p.models.length > 0
        ? p.models
        : p.model
          ? [p.model]
          : [],
  }))
  const currentValue = provider && model ? encodeOption(provider, model) : ''

  return (
    <div className="border-t border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            // Enter sends unless Shift is held (newline). Escape clears.
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            } else if (e.key === 'Escape') {
              setValue('')
            }
          }}
          placeholder="Ask about your indexed documentation…"
          rows={1}
          className="max-h-40 min-h-[2.5rem] flex-1 resize-y rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm outline-none focus:border-blue-400 focus:bg-white focus:ring-1 focus:ring-blue-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:bg-slate-800"
        />
        <select
          value={currentValue}
          onChange={(e) => onSelectionChange(e.target.value)}
          disabled={disabled || available.length === 0}
          aria-label="LLM provider and model"
          title="LLM provider and model"
          className="h-10 max-w-[10rem] rounded-xl border border-slate-200 bg-slate-50 px-2 text-xs text-slate-600 outline-none focus:border-blue-400 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
        >
          <option value="">
            {available.length === 0 ? 'No provider' : 'Auto'}
          </option>
          {optionGroups.map((group) => (
            <optgroup key={group.name} label={group.name}>
              {group.models.map((m) => (
                <option key={m} value={encodeOption(group.name, m)}>
                  {m}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send size={16} />
        </button>
      </div>
      <p className="mx-auto mt-1.5 flex max-w-3xl items-center gap-1 text-[11px] text-slate-400 dark:text-slate-500">
        <Cpu size={11} />
        {available.length > 0
          ? `Model: ${provider ?? 'auto'}${model ? ` · ${model}` : ''}`
          : 'No LLM provider configured — set an API key or start Ollama'}
      </p>
    </div>
  )
}
