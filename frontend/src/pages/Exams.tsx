import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, fmtScore, pad, TYPE_NAMES, type QuizSession } from '../api'
import QuizRunner, { QuizResult } from '../components/QuizRunner'
import { useToast } from '../components/Toast'
import { useLoad } from '../useLoad'
import { Loading } from './common'

interface ExamsData {
  phases: {
    phase: number; title: string; goals: string[]; available: boolean; why: string; passed: boolean
    pending: number | null; history: { id: number; score: number; passed: boolean; date: string }[]
  }[]
  pass_score: number
  paper: Record<string, { count: number; points: number }>
}

export default function Exams() {
  const { data, error, reload } = useLoad<ExamsData>('/api/exams')
  const [s, setS] = useState<QuizSession | null>(null)
  const toast = useToast()
  const nav = useNavigate()

  async function open(phase: number) {
    try {
      setS(await api.post<QuizSession>(`/api/exams/${phase}`))
      window.scrollTo(0, 0)
    } catch (e) {
      toast((e as Error).message)
    }
  }
  async function view(id: number) {
    try {
      setS(await api.get<QuizSession>(`/api/sessions/${id}`))
      window.scrollTo(0, 0)
    } catch (e) {
      toast((e as Error).message)
    }
  }

  if (!data) return <Loading error={error} />
  if (s) {
    const ph = s.ref
    return (
      <>
        <div className="small" style={{ marginBottom: 6 }}><a href="#" onClick={(e) => { e.preventDefault(); setS(null); reload() }}>← 阶段卷</a></div>
        <h1>第 {ph} 阶段卷 · {data.phases[ph - 1].title}</h1>
        {s.submitted ? (
          <>
            <QuizResult s={s} />
            <div className="pager">
              <button className="btn" onClick={() => { setS(null); reload() }}>返回</button>
              {s.passed && ph < 5 ? (
                <button className="btn primary" onClick={() => nav(`/day/${ph * 10 + 1}`)}>进入 Day {pad(ph * 10 + 1)}</button>
              ) : !s.passed ? (
                <button className="btn primary" onClick={() => open(ph)}>换一套再考</button>
              ) : null}
            </div>
          </>
        ) : (
          <>
            <div className="small" style={{ marginBottom: 10 }}>44 题，约 40 分钟。作答自动保存，可以分几次做完；交卷后才显示答案。</div>
            <QuizRunner s={s} onSubmitted={setS} />
          </>
        )}
      </>
    )
  }

  const paper = Object.entries(data.paper).map(([t, v]) => `${TYPE_NAMES[t]} ${v.count}×${v.points}`).join(' + ')
  return (
    <>
      <h1>阶段卷</h1>
      <div className="small" style={{ marginBottom: 12 }}>
        每 10 天一张卷，满分 100：{paper}。题目覆盖这 10 天（每天都有），多选题少选得一半分。<b>≥{data.pass_score} 分解锁下一阶段</b>，没过可以换一套重考。
      </div>
      {data.phases.map((p) => (
        <div className="card" key={p.phase}>
          <div className="between">
            <div>
              <h3 style={{ margin: 0 }}>第 {p.phase} 阶段 · {p.title} <span className="small">Day {pad((p.phase - 1) * 10 + 1)}–{pad(p.phase * 10)}</span></h3>
              {!p.available && <div className="small">🔒 {p.why}</div>}
            </div>
            <div className="row">
              {p.passed && <span className="pill ok">已通过</span>}
              {p.available && (
                <button className={'btn' + (p.passed ? '' : ' primary')} onClick={() => open(p.phase)}>
                  {p.pending ? '继续作答' : p.history.length ? '再考一次' : '开始考试'}
                </button>
              )}
            </div>
          </div>
          <details className="ref">
            <summary>这一阶段要达到的能力</summary>
            <ul className="plain">{p.goals.map((g) => <li key={g}>{g}</li>)}</ul>
          </details>
          {p.history.length > 0 && (
            <div className="row mt">
              {p.history.map((h) => (
                <button key={h.id} className={'pill ' + (h.passed ? 'ok' : 'bad')} onClick={() => view(h.id)} title="查看这次的答卷">
                  {h.date.slice(5)} · {fmtScore(h.score)} 分
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
      <div className="small mt">想看某阶段每个知识点的掌握情况，去 <Link to="/reports">学习报告</Link>。</div>
    </>
  )
}
