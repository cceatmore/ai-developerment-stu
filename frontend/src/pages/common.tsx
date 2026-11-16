export function Loading({ error }: { error?: string | null }) {
  if (error) return <div className="banner">加载失败：{error}</div>
  return <div className="empty">加载中…</div>
}
