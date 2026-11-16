import { useState } from 'react'
import { Link } from 'react-router-dom'
import { fmtScore, OBJECTIVE, pad, type Question } from '../api'
import Markdown from '../components/Markdown'
import QuestionCard from '../components/QuestionCard'
import { useLoad } from '../useLoad'
import { Loading } from './common'

interface ReviewData {
  needed: boolean
  done: boolean
  size: number
  gap: number
  current_day: number
  interview_pending: { day: number; title: string; done: number; total: number }[]
  due_kps: number
  upcoming: { kp_name: string; date: string }[]
  history: { id: number; date: string; score: number | null; total: number }[]
}

interface WrongRow {
  question_id: string
  wrong_count: number
  right_streak: number
  last_answer: string
  last_score: number
  updated_at: string
  question: Question
}

export default function Review() {
  const [tab, setTab] = useState<'today' | 'wrong' | 'resolved'>('today')
  return (
    <>
      <h1>复习与错题</h1>
      <div className="tabs">
        <button className={tab === 'today' ? 'on' : ''} onClick={() => setTab('today')}>复习安排</button>
        <button className={tab === 'wrong' ? 'on' : ''} onClick={() => setTab('wrong')}>错题本</button>
        <button className={tab === 'resolved' ? 'on' : ''} onClick={() => setTab('resolved')}>已纠正</button>
      </div>
      {tab === 'today' ? <Today /> : <WrongBook resolved={tab === 'resolved'} />}
    </>
  )
}

function Today() {
  const { data, error } = useLoad<ReviewData>('/api/review')
  if (!data) return <Loading error={error} />
  return (
    <>
      <div className="card">
        <div className="between">
          <h3 style={{ margin: 0 }}>今天的复习</h3>
          {data.needed ? (
            <Link to={`/day/${data.current_day}`} className="btn primary">去复习 {data.size} 题</Link>
          ) : (
            <span className="pill ok">{data.done ? '已完成' : '今天不需要'}</span>
          )}
        </div>
        <ul className="plain mt">
          <li>每天第一次打开先做一组复习（全是选择题）。<b>基础 8 题，每多隔 1 天加 4 题</b>，最多 20 题。所以周一、休假回来会多一些。</li>
          <li>出题顺序：错题 → 到期复习（第 1、2、4、7、16 天）→ 掌握不扎实 → 超过 7 天没碰过的旧知识。</li>
          <li>错题在复习或错题本里<b>连续两次答对</b>才算纠正。</li>
        </ul>
        {data.history.length > 0 && (
          <>
            <div className="label">最近的复习</div>
            <div className="row">{data.history.map((h) => <span key={h.id} className="pill">{h.date.slice(5)} · {fmtScore(h.score)} 分 / {h.total} 题</span>)}</div>
          </>
        )}
      </div>
      <div className="grid g2 mt">
        <div className="card">
          <h3>还没写完的面试题</h3>
          {data.interview_pending.length ? (
            data.interview_pending.map((p) => (
              <div className="list-item" key={p.day}>
                <Link to={`/day/${p.day}`}>Day {pad(p.day)} · {p.title}</Link>
                <span className="small">{p.done}/{p.total}</span>
              </div>
            ))
          ) : (
            <div className="small">全部写完了。</div>
          )}
        </div>
        <div className="card">
          <h3>接下来到期的知识点</h3>
          {data.upcoming.length ? (
            data.upcoming.slice(0, 10).map((u, i) => <div className="list-item" key={i}><span>{u.kp_name}</span><span className="small">{u.date}</span></div>)
          ) : (
            <div className="small">暂无。</div>
          )}
        </div>
      </div>
    </>
  )
}

function WrongBook({ resolved }: { resolved: boolean }) {
  const { data, error, reload } = useLoad<WrongRow[]>(`/api/wrong?resolved=${resolved}`)
  const [open, setOpen] = useState<string | null>(null)
  if (!data) return <Loading error={error} />
  if (!data.length) return <div className="card empty">{resolved ? '还没有纠正过的错题。' : '错题本是空的。'}</div>
  const toggle = (id: string) => {
    if (open) reload()
    setOpen(open === id ? null : id)
  }
  return (
    <div className="card">
      <div className="small">共 {data.length} 题。重做时答对 2 次算纠正。</div>
      {data.map((w) => (
        <div key={w.question_id} className="wrong-row">
          <div className="between">
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="small">
                {w.question.kp_name} · Day {pad(w.question.day ?? 0)} · 错 {w.wrong_count} 次 · 最近 {fmtScore(w.last_score)} 分
                {!resolved && w.right_streak > 0 ? ` · 已连续答对 ${w.right_streak} 次` : ''}
              </div>
              <Markdown>{w.question.question.length > 160 ? w.question.question.slice(0, 160) + '…' : w.question.question}</Markdown>
            </div>
            {!resolved && <button className="btn" onClick={() => toggle(w.question_id)}>{open === w.question_id ? '收起' : '重做'}</button>}
          </div>
          {open === w.question_id && (
            <div className="mt">
              {w.last_answer && !OBJECTIVE.includes(w.question.type) && (
                <div className="mine"><div className="label">上次的回答</div><div className="pre-wrap">{w.last_answer}</div></div>
              )}
              <div className="mt">
                <QuestionCard q={w.question} context="wrong" allowRetry={false} />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
