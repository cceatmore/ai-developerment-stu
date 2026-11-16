import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useToast } from '../components/Toast'
import { useLoad } from '../useLoad'
import { Loading } from './common'

interface Status {
  days: number[]
  kps: number
  questions: number
  projects: string[]
  modules: number
  errors: string[]
}

export default function Settings() {
  const { data, error, reload } = useLoad<Status>('/api/content/status')
  const kps = useLoad<{ id: string; name: string; day: number; outdated: boolean }[]>('/api/kps')
  const toast = useToast()
  const file = useRef<HTMLInputElement>(null)

  async function reloadContent() {
    try {
      const r = await api.post<{ days: number; errors: string[] }>('/api/content/reload')
      toast(`已重新加载：${r.days} 天${r.errors.length ? `，${r.errors.length} 个文件有错误` : ''}`, r.errors.length ? 'error' : 'ok')
      reload()
    } catch (e) {
      toast((e as Error).message)
    }
  }
  async function importFile(f: File) {
    if (!confirm('导入会用备份文件覆盖当前全部学习记录。建议先导出一份当前数据。确定继续？')) return
    try {
      const json = JSON.parse(await f.text())
      await api.post('/api/import', json)
      toast('导入完成', 'ok')
    } catch (e) {
      toast('导入失败：' + (e as Error).message)
    }
  }

  if (!data) return <Loading error={error} />
  const missing = Array.from({ length: 50 }, (_, i) => i + 1).filter((d) => !data.days.includes(d))
  const outdated = (kps.data ?? []).filter((k) => k.outdated)

  return (
    <>
      <h1>数据与设置</h1>
      <div className="card">
        <h3>学习数据</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          所有记录保存在本机 <code>data/study.db</code>（SQLite），不上传任何服务器。每次启动自动备份到 <code>data/backups/</code>，保留最近 14 天。
        </p>
        <div className="row">
          <a className="btn primary" href="/api/export" download>导出全部数据（JSON）</a>
          <a className="btn" href="/api/export/markdown" target="_blank" rel="noreferrer">导出学习记录（Markdown）</a>
          <button className="btn ghost" onClick={() => file.current?.click()}>从备份导入…</button>
          <input ref={file} type="file" accept=".json" hidden onChange={(e) => e.target.files?.[0] && importFile(e.target.files[0])} />
        </div>
      </div>

      <div className="card">
        <div className="between">
          <h3 style={{ margin: 0 }}>课程内容</h3>
          <button className="btn" onClick={reloadContent}>重新加载内容</button>
        </div>
        <p className="muted">
          已加载 {data.days.length}/50 天 · {data.kps} 个知识点 · {data.questions} 道题 · 项目 {data.projects.length}/3（{data.modules} 个模块）
        </p>
        <div className="small">
          内容是 <code>content/</code> 目录下的 YAML 文件，可以直接修改（例如更新过时的框架写法），改完点「重新加载内容」即可生效，学习记录不受影响。编写规范见 <code>content/AUTHORING.md</code>。
        </div>
        {missing.length > 0 && <div className="banner mt">缺少或未通过校验的天数：{missing.join('、')}</div>}
        {data.errors.map((e, i) => (
          <pre key={i} className="banner" style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{e}</pre>
        ))}
      </div>

      <div className="card">
        <h3>标记为过时/有误的知识点（{outdated.length}）</h3>
        {outdated.length ? (
          outdated.map((k) => (
            <div className="list-item" key={k.id}>
              <Link to={`/day/${k.day}`}>Day {String(k.day).padStart(2, '0')} · {k.name}</Link>
              <span className="small">content/days/day{String(k.day).padStart(2, '0')}.yaml · {k.id}</span>
            </div>
          ))
        ) : (
          <div className="small">学习时在知识点底部点「标记内容过时/有误」，这里会集中列出，方便之后统一更新。</div>
        )}
      </div>

      <div className="card">
        <h3>评分说明</h3>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          <li>选择题自动判分；多选题少选不错选得一半分，错选 0 分。</li>
          <li>当天测试 12 题，≥70 分解锁下一天；每 10 天一张阶段卷（满分 100），≥70 分解锁下一阶段。</li>
          <li>面试题先作答，再对照评分要点逐条自评（说到了 1 / 部分 0.5 / 没说到 0）；面试题另有 15% 的表达分。</li>
          <li>答错的题进入错题本；连续两次答对才算纠正。</li>
          <li>掌握程度：基本掌握需要在至少 2 个不同日子作答、最近平均 ≥70；熟练掌握需要 3 个不同日子、最近平均 ≥85。</li>
          <li>系统不调用 AI。需要更严格的评价时，用题目下方的「复制给 AI 评审」，粘贴到 Cursor 等工具里。</li>
        </ul>
      </div>
    </>
  )
}
