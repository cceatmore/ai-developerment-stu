import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import Mermaid from './Mermaid'

type HastNode = { type: string; value?: string; children?: HastNode[] }

function textOf(node: HastNode): string {
  if (node.type === 'text') return node.value ?? ''
  return (node.children ?? []).map(textOf).join('')
}

export default function Markdown({ children }: { children: string | null | undefined }) {
  if (!children) return null
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
          pre: ({ children, node }) => {
            const codeEl = node?.children?.[0]
            const cls = codeEl && 'properties' in codeEl ? String((codeEl.properties?.className as string[] | undefined)?.join(' ') ?? '') : ''
            if (cls.includes('language-mermaid') && codeEl) {
              return <Mermaid code={textOf(codeEl).trim()} />
            }
            return <pre>{children}</pre>
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}

export function CodeBlock({ code, language = 'python' }: { code: string; language?: string }) {
  return <Markdown>{'```' + language + '\n' + code.replace(/\n$/, '') + '\n```'}</Markdown>
}
