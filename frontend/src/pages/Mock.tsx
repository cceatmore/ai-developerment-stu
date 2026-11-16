import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, fmtScore, pad, type Attempt, type Question } from '../api'
import Markdown from '../components/Markdown'
import QuestionCard, { QBody, QHead } from '../components/QuestionCard'
import { useToast } from '../components/Toast'
import { useLoad } from '../useLoad'
import { Loading } from './common'
import { ScoreBar } from './Dashboard'

export interface MockReport {
  mode: string
  total: number
  answered: number
  overall: number | null
  categories: Record<string, number | null>
  expression: number | null
  weak: { question: string; score: number; name: string | null; day: number | null }[]
  verdict: string
  note: string
}

interface Session {
  id: number
  mode: string
  mode_name: string
  created_at: string
  finished: boolean
  locked: boolean
  answers: Record<string, string>
  questions: Question[]
  attempts: Record<string, Attempt>
  report: MockReport | null
  background: string | null
}

const MODES: [string, string, string][] = [
  ['mixed', '综合面试', '从已通过的天数的面试题里抽 6 道，覆盖不同方向，由易到难。'],
  ['p1', '项目深挖 · 企业知识库 RAG', '面试官围绕项目 1 连续追问：切片、检索、评测、权限、成本。'],
  ['p2', '项目深挖 · 智慧园区运营 Agent', '围绕项目 2：Agent 循环、工具可靠性、人工审批、MCP、可观测。'],
  ['p3', '项目深挖 · 前端 Coding Agent', '围绕项目 3：上下文工程、沙箱、补丁与回滚、评测。'],
]

export default function Mock() {
  const { id } = useParams()
  return id ? <SessionView id={Number(id)} /> : <Home />
}

function Home() {
  const nav = useNavigate()
  const toast = useToast()
  const hist = useLoad<{ id: number; mode: string; mode_name: string; created_at: string; finished: boolean; total: number; overall: number | null }[]>('/api/mock')
  const [busy, setBusy] = useState(false)

  async function start(mode: string) {
    setBusy(true)
    try {
      const s = await api.post<Session>('/api/mock', { mode })
      nav(`/mock/${s.id}`)
    } catch (e) {
      toast((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <h1>模拟面试</h1>
      <div className="small" style={{ marginBottom: 12 }}>
        像真实面试一样：<b>先全部作答（看不到答案）</b>，交卷后逐题对照要点自评，最后生成报告。建议在有整块时间时做，约 30–40 分钟。
      </div>
      <div className="grid g2">
        {MODES.map(([m, name, desc]) => (
          <button key={m} className="card mode-card" disabled={busy} onClick={() => start(m)}>
            <h3>{name}</h3>
            <div className="muted">{desc}</div>
          </button>
        ))}
      </div>
      <div className="card mt">
        <h3>历史记录</h3>
        {!hist.data?.length ? (
          <div className="small">还没有模拟面试记录。</div>
        ) : (
          hist.data.map((h) => (
            <div className="list-item" key={h.id}>
              <Link to={`/mock/${h.id}`}>{h.mode_name} · {h.created_at.replace('T', ' ').slice(0, 16)}</Link>
              {h.finished ? <span className="pill">{fmtScore(h.overall)} 分</span> : <span className="pill warn">未完成</span>}
            </div>
          ))
        )}
      </div>
    </>
  )
}

function SessionView({ id }: { id: number }) {
  const { data: s, error, reload } = useLoad<Session>(`/api/mock/${id}`)
  if (!s) return <Loading error={error} />
  return (
    <>
      <div className="small" style={{ marginBottom: 6 }}><Link to="/mock">← 模拟面试</Link></div>
      <h1>{s.mode_name}</h1>
      <div className="small">{s.created_at.replace('T', ' ')} · 共 {s.questions.length} 题</div>
      {s.background && (
        <details className="ref" open={!s.locked}>
          <summary>项目背景（先读一遍）</summary>
          <Markdown>{s.background}</Markdown>
        </details>
      )}
      <div className="mt">
        {!s.locked ? <Answering s={s} reload={reload} /> : <Grading s={s} reload={reload} />}
      </div>
    </>
  )
}

function Answering({ s, reload }: { s: Session; reload: () => void }) {
  const [i, setI] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>(s.answers)
  const timer = useRef<number | undefined>(undefined)
  const toast = useToast()
  const q = s.questions[i]

  useEffect(() => () => window.clearTimeout(timer.current), [])

  function onText(v: string) {
    setAnswers((a) => ({ ...a, [q.id]: v }))
    window.clearTimeout(timer.current)
    const qid = q.id
    timer.current = window.setTimeout(() => {
      api.put(`/api/mock/${s.id}/answer`, { question_id: qid, text: v }).catch((e) => toast(e.message))
    }, 500)
  }
  async function submit() {
    const empty = s.questions.filter((x) => !(answers[x.id] ?? '').trim()).length
    if (!confirm(empty ? `还有 ${empty} 题没有作答。确定交卷？` : '确定交卷？交卷后不能修改回答。')) return
    window.clearTimeout(timer.current)
    try {
      await api.put(`/api/mock/${s.id}/answer`, { question_id: q.id, text: answers[q.id] ?? '' })
      await api.post(`/api/mock/${s.id}/lock`)
      reload()
    } catch (e) {
      toast((e as Error).message)
    }
  }
  return (
    <>
      <div className="qnav">
        {s.questions.map((x, j) => (
          <button key={x.id} className={(j === i ? 'on ' : '') + ((answers[x.id] ?? '').trim() ? 'answered' : '')} onClick={() => setI(j)}>{j + 1}</button>
        ))}
      </div>
      <div className="qcard">
        <QHead q={q} />
        <QBody q={q} />
        <textarea className="answer" value={answers[q.id] ?? ''} onChange={(e) => onText(e.target.value)} placeholder="像面试时说话一样作答，写要点也可以。自动保存；交卷前不显示参考答案。" />
      </div>
      <div className="pager">
        <span className="small">第 {i + 1} / {s.questions.length} 题</span>
        <div className="row">
          {i > 0 && <button className="btn" onClick={() => setI(i - 1)}>上一题</button>}
          {i < s.questions.length - 1 ? (
            <button className="btn primary" onClick={() => setI(i + 1)}>下一题</button>
          ) : (
            <button className="btn primary" onClick={submit}>交卷</button>
          )}
        </div>
      </div>
    </>
  )
}

function Grading({ s, reload }: { s: Session; reload: () => void }) {
  const [i, setI] = useState(() => {
    const idx = s.questions.findIndex((q) => !s.attempts[q.id])
    return idx < 0 ? 0 : idx
  })
  const toast = useToast()
  const q = s.questions[i]
  const graded = s.questions.filter((x) => s.attempts[x.id]).length

  async function finish() {
    const left = s.questions.length - graded
    if (left && !confirm(`还有 ${left} 题没有自评，结束后这些题不计入报告。确定结束？`)) return
    try {
      await api.post(`/api/mock/${s.id}/finish`)
      reload()
      window.scrollTo(0, 0)
    } catch (e) {
      toast((e as Error).message)
    }
  }

  return (
    <>
      {s.finished && s.report ? <MockReportView r={s.report} /> : <div className="banner">已交卷。逐题对照要点自评，全部评完后生成报告。</div>}
      <div className="qnav mt">
        {s.questions.map((x, j) => {
          const a = s.attempts[x.id]
          return (
            <button key={x.id} className={(j === i ? 'on ' : '') + (a ? (a.score >= 80 ? 'good' : a.score >= 60 ? 'mid' : 'bad') : '')} onClick={() => setI(j)}>{j + 1}</button>
          )
        })}
      </div>
      <QuestionCard
        key={q.id}
        q={q}
        context="mock"
        sessionId={s.id}
        existing={s.attempts[q.id]}
        presetAnswer={s.attempts[q.id] ? undefined : s.answers[q.id] ?? ''}
        allowRetry={false}
        onDone={() => reload()}
      />
      <div className="pager">
        <span className="small">已自评 {graded} / {s.questions.length}</span>
        <div className="row">
          {i > 0 && <button className="btn" onClick={() => setI(i - 1)}>上一题</button>}
          {i < s.questions.length - 1 && <button className="btn" onClick={() => setI(i + 1)}>下一题</button>}
          {!s.finished && <button className={'btn' + (graded === s.questions.length ? ' primary' : '')} onClick={finish}>生成报告</button>}
        </div>
      </div>
    </>
  )
}

export function MockReportView({ r }: { r: MockReport }) {
  return (
    <div className="card">
      <div className="between">
        <h2 style={{ margin: 0 }}>面试报告</h2>
        <span className="pill pri">总分 {fmtScore(r.overall)}</span>
      </div>
      <p>{r.verdict}</p>
      <div className="grid g2">
        <div>
          <div className="label">分方向得分</div>
          {Object.entries(r.categories).map(([k, v]) => <ScoreBar key={k} name={k} value={v} />)}
          <ScoreBar name="表达" value={r.expression} />
        </div>
        <div>
          <div className="label">需要加强（低于 70 分）</div>
          {r.weak.length ? (
            r.weak.map((w, i) => (
              <div key={i} className="list-item">
                <span>{w.name ?? '项目题'}<div className="small">{w.question}</div></span>
                {w.day ? <Link to={`/day/${w.day}`} className="small">Day {pad(w.day)} · {fmtScore(w.score)} 分</Link> : <span className="small">{fmtScore(w.score)} 分</span>}
              </div>
            ))
          ) : (
            <div className="small">没有低于 70 分的题。</div>
          )}
        </div>
      </div>
      <div className="small mt">作答 {r.answered}/{r.total} 题。{r.note}</div>
    </div>
  )
}
