import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORY_NAMES, fmtScore, pad, TYPE_NAMES, type DailyReport, type KpResult, type Level } from '../api'
import { useLoad } from '../useLoad'
import { Loading } from './common'
import { ScoreBar } from './Dashboard'
import { DailyReportView } from './Daily'

interface KpRow {
  id: string
  name: string
  level: Level
  day: number
  learned: boolean
  first_score: number | null
  last_score: number | null
  attempts: number
  wrong_count: number
  mastery: number
  mastery_name: string
  next_review: string | null
  note: string
}

interface PhaseReport {
  session_id: number
  score: number
  passed: boolean
  result: { kps: KpResult[]; weak: KpResult[]; by_type: Record<string, { got: number; total: number }> }
}

interface Final {
  generated_at: string
  finished_course: boolean
  ability: {
    attempts: number
    objective_accuracy: number | null
    interview_score: number | null
    scenario: number | null
    categories: Record<string, number | null>
    learned: number
    mastered: number
    total_kps: number
  }
  exams: Record<string, number>
  projects: { id: string; title: string; done: number; total: number }[]
  mastered: { id: string; name: string; level: Level; day: number; mastery_name: string }[]
  not_mastered: { id: string; name: string; level: Level; day: number; mastery: number; mastery_name: string; last_score: number | null }[]
  shortfalls: string[]
  roles: { role: string; score: number }[]
  roles_note: string
  before_interview: string[]
  note: string
  phases: Record<string, string>
}

export default function Reports() {
  const [tab, setTab] = useState<'kps' | 'daily' | 'phase' | 'final'>('kps')
  return (
    <>
      <h1>学习报告</h1>
      <div className="tabs">
        <button className={tab === 'kps' ? 'on' : ''} onClick={() => setTab('kps')}>知识点掌握</button>
        <button className={tab === 'daily' ? 'on' : ''} onClick={() => setTab('daily')}>每日总结</button>
        <button className={tab === 'phase' ? 'on' : ''} onClick={() => setTab('phase')}>阶段卷</button>
        <button className={tab === 'final' ? 'on' : ''} onClick={() => setTab('final')}>能力报告</button>
      </div>
      {tab === 'kps' && <KpTable />}
      {tab === 'daily' && <ReportList kind="daily" />}
      {tab === 'phase' && <ReportList kind="phase" />}
      {tab === 'final' && <FinalReport />}
    </>
  )
}

function KpTable() {
  const { data, error } = useLoad<KpRow[]>('/api/kps')
  const [filter, setFilter] = useState<'learned' | 'weak' | 'all'>('learned')
  const rows = useMemo(() => {
    if (!data) return []
    if (filter === 'all') return data
    if (filter === 'weak') return data.filter((k) => k.learned && k.mastery < 3)
    return data.filter((k) => k.learned)
  }, [data, filter])
  if (!data) return <Loading error={error} />
  return (
    <div className="card">
      <div className="between" style={{ marginBottom: 10 }}>
        <div className="row">
          <select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)}>
            <option value="learned">已学知识点</option>
            <option value="weak">未达到基本掌握</option>
            <option value="all">全部 50 天</option>
          </select>
          <span className="small">共 {rows.length} 个</span>
        </div>
        <span className="small">掌握程度只看作答：在不同日子里答对才会升级</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="t">
          <thead>
            <tr><th>天</th><th>知识点</th><th>掌握</th><th>首次</th><th>最近</th><th>作答</th><th>答错</th><th>下次复习</th></tr>
          </thead>
          <tbody>
            {rows.map((k) => (
              <tr key={k.id}>
                <td><Link to={`/day/${k.day}`}>{pad(k.day)}</Link></td>
                <td><span className={'tag ' + k.level.toLowerCase()}>{k.level}</span>{k.name}{k.note ? <span className="small" title={k.note}> 📝</span> : null}</td>
                <td><span className={'pill ' + (k.mastery >= 3 ? 'ok' : k.mastery === 2 ? 'warn' : '')}>{k.mastery_name}</span></td>
                <td>{fmtScore(k.first_score)}</td>
                <td>{fmtScore(k.last_score)}</td>
                <td>{k.attempts}</td>
                <td>{k.wrong_count || ''}</td>
                <td>{k.next_review ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ReportList({ kind }: { kind: 'daily' | 'phase' }) {
  const { data, error } = useLoad<{ id: number; kind: string; ref: number; created_at: string; data: unknown }[]>('/api/reports')
  const [open, setOpen] = useState<number | null>(null)
  if (!data) return <Loading error={error} />
  const list = data.filter((r) => r.kind === kind).sort((a, b) => b.ref - a.ref || b.id - a.id)
  if (!list.length) {
    return <div className="card empty">{kind === 'daily' ? '当天测试通过后会生成每日总结。' : '学完 Day 10 后可以考第 1 阶段卷。'}</div>
  }
  return (
    <>
      {list.map((r) => {
        const title = kind === 'daily'
          ? `Day ${pad(r.ref)} · ${(r.data as DailyReport).title} · 测试 ${fmtScore((r.data as DailyReport).test_score)} 分`
          : `第 ${r.ref} 阶段卷 · ${fmtScore((r.data as PhaseReport).score)} 分 · ${(r.data as PhaseReport).passed ? '通过' : '未通过'}`
        return (
          <div key={r.id} style={{ marginBottom: 12 }}>
            <button className="card" style={{ width: '100%', textAlign: 'left' }} onClick={() => setOpen(open === r.id ? null : r.id)}>
              <div className="between">
                <b>{title}</b>
                <span className="small">{r.created_at.replace('T', ' ').slice(0, 16)}</span>
              </div>
            </button>
            {open === r.id && <div className="mt">{kind === 'daily' ? <DailyReportView r={r.data as DailyReport} /> : <PhaseView r={r.data as PhaseReport} />}</div>}
          </div>
        )
      })}
    </>
  )
}

function PhaseView({ r }: { r: PhaseReport }) {
  return (
    <div className="card">
      <div className="row">
        {Object.entries(r.result.by_type ?? {}).map(([t, v]) => <span key={t} className="pill">{TYPE_NAMES[t]} {v.got}/{v.total}</span>)}
      </div>
      <div className="label">低于 70 分的知识点（{r.result.weak.length}）</div>
      {r.result.weak.length ? (
        r.result.weak.map((k) => (
          <div className="list-item" key={k.id}>
            <Link to={`/day/${k.day}`}>Day {pad(k.day)} · {k.name}</Link>
            <span className="small">{fmtScore(k.avg)} 分 · {k.mastery_name}</span>
          </div>
        ))
      ) : (
        <div className="small">没有。</div>
      )}
    </div>
  )
}

function FinalReport() {
  const { data: r, error } = useLoad<Final>('/api/reports/final')
  if (!r) return <Loading error={error} />
  const ab = r.ability
  return (
    <>
      {!r.finished_course && <div className="banner">课程还没学完，下面是根据目前作答记录生成的中期快照。</div>}
      <div className="grid g4">
        <div className="card stat"><div className="lbl">选择题正确率</div><div className="num">{fmtScore(ab.objective_accuracy)}</div><div className="small">系统判分</div></div>
        <div className="card stat"><div className="lbl">面试题自评</div><div className="num">{fmtScore(ab.interview_score)}</div><div className="small">最近 30 次</div></div>
        <div className="card stat"><div className="lbl">场景 / 设计题</div><div className="num">{fmtScore(ab.scenario)}</div><div className="small">面试官最爱问</div></div>
        <div className="card stat"><div className="lbl">基本掌握的知识点</div><div className="num">{ab.mastered} / {ab.total_kps}</div><div className="small">已学 {ab.learned}</div></div>
      </div>
      <div className="grid g2 mt">
        <div className="card">
          <h3>各方向得分</h3>
          {Object.entries(ab.categories).map(([k, v]) => <ScoreBar key={k} name={CATEGORY_NAMES[k]} value={v} />)}
          <div className="label">阶段卷最高分</div>
          <div className="row">
            {[1, 2, 3, 4, 5].map((p) => <span key={p} className={'pill ' + ((r.exams[p] ?? 0) >= 70 ? 'ok' : '')}>第 {p} 阶段 {r.exams[p] !== undefined ? fmtScore(r.exams[p]) : '—'}</span>)}
          </div>
          <div className="label">项目</div>
          {r.projects.map((p) => <div className="list-item" key={p.id}><span>{p.title}</span><span className="small">{p.done}/{p.total} 模块</span></div>)}
        </div>
        <div className="card">
          <h3>可以投递的方向</h3>
          {r.roles.length ? r.roles.map((x) => <div className="list-item" key={x.role}><span>{x.role}</span><span className="pill ok">{x.score}</span></div>) : <div className="muted">目前还没有达到推荐标准的方向。</div>}
          <div className="small mt">{r.roles_note}</div>
          <h3 className="mt">还存在的短板</h3>
          {r.shortfalls.length ? <ul className="plain">{r.shortfalls.map((s) => <li key={s}>{s}</li>)}</ul> : <div className="small">暂无明显短板。</div>}
        </div>
      </div>
      <div className="grid g2 mt">
        <div className="card">
          <h3>面试前先补（P0 优先）</h3>
          {r.before_interview.length ? <ul className="plain">{r.before_interview.map((s) => <li key={s}>{s}</li>)}</ul> : <div className="small">P0 知识点都已基本掌握。</div>}
        </div>
        <div className="card">
          <h3>已掌握（{r.mastered.length}）</h3>
          <div style={{ maxHeight: 260, overflowY: 'auto' }}>
            {r.mastered.length ? r.mastered.map((k) => <div key={k.id} className="list-item"><span><span className={'tag ' + k.level.toLowerCase()}>{k.level}</span>{k.name}</span><span className="small">{k.mastery_name}</span></div>) : <div className="small">暂无</div>}
          </div>
        </div>
      </div>
      <div className="small mt">生成于 {r.generated_at.replace('T', ' ')}。{r.note}</div>
    </>
  )
}
