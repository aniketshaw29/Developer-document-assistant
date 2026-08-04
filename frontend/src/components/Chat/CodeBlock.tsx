import { Children, useMemo, useState } from 'react'
import type { ReactElement, ReactNode } from 'react'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import cpp from 'highlight.js/lib/languages/cpp'
import css from 'highlight.js/lib/languages/css'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import rust from 'highlight.js/lib/languages/rust'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'
import { Check, Copy } from 'lucide-react'

// Register the subset of languages we care about to keep the bundle lean.
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('css', css)
hljs.registerLanguage('go', go)
hljs.registerLanguage('java', java)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('python', python)
hljs.registerLanguage('rust', rust)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('yaml', yaml)

interface CodeBlockProps {
  /** The <code> element react-markdown renders inside <pre>. */
  children?: ReactNode
}

/**
 * Renders a highlighted <pre> block with a copy button.
 * Used as the `pre` renderer for assistant markdown messages.
 */
export default function CodeBlock({ children }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  // Extract the code text + language from the child <code> element.
  const { code, language } = useMemo(() => {
    const child = Children.only(children) as ReactElement<{
      className?: string
      children?: ReactNode
    }>
    const raw = String(child.props.children ?? '').replace(/\n$/, '')
    const match = /language-(\w+)/.exec(child.props.className ?? '')
    return { code: raw, language: match?.[1] ?? '' }
  }, [children])

  // Highlight with the explicit language, or auto-detect.
  const highlighted = useMemo(() => {
    try {
      return language
        ? hljs.highlight(code, { language }).value
        : hljs.highlightAuto(code).value
    } catch {
      // Unknown language — fall back to auto-detect, then plain text.
      try {
        return hljs.highlightAuto(code).value
      } catch {
        return code
      }
    }
  }, [code, language])

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard unavailable — silently ignore.
    }
  }

  return (
    <div className="group relative my-3 overflow-hidden rounded-lg border border-slate-700">
      <div className="flex items-center justify-between bg-slate-800 px-3 py-1.5">
        <span className="font-mono text-[11px] text-slate-400">
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={copyCode}
          aria-label="Copy code"
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-slate-400 transition hover:text-slate-200"
        >
          {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 text-[13px] leading-relaxed">
        <code
          className="hljs"
          dangerouslySetInnerHTML={{ __html: highlighted }}
        />
      </pre>
    </div>
  )
}
