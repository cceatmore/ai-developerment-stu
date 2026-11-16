import { useEffect, useRef, useState } from 'react'

let seq = 0
let loader: Promise<typeof import('mermaid').default> | null = null

function loadMermaid() {
  if (!loader) {
    loader = import('mermaid').then((m) => {
      m.default.initialize({
        startOnLoad: false,
        theme: 'neutral',
        securityLevel: 'strict',
        fontFamily: '-apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
        themeVariables: { fontSize: '15px' },
        flowchart: { htmlLabels: true, curve: 'basis' },
      })
      return m.default
    })
  }
  return loader
}
;(window as unknown as { __loadMermaid?: unknown }).__loadMermaid = loadMermaid

export default function Mermaid({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const id = `mmd-${++seq}`
    loadMermaid()
      .then((m) => m.render(id, code))
      .then(({ svg }) => {
        if (alive && ref.current) ref.current.innerHTML = svg
      })
      .catch((e: unknown) => {
        document.getElementById(id)?.remove()
        document.getElementById('d' + id)?.remove()
        if (alive) setError(e instanceof Error ? e.message : String(e))
      })
    return () => {
      alive = false
    }
  }, [code])

  if (error) {
    return (
      <div className="diagram-error">
        <div className="small">图表渲染失败，以下是图表源码：</div>
        <pre>{code}</pre>
      </div>
    )
  }
  return <div className="diagram" ref={ref} />
}
