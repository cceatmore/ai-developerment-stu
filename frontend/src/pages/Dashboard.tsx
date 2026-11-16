import { Link, useNavigate } from 'react-router-dom'
import { CATEGORY_NAMES, fmtScore, pad, type DayState, type Level, type ReviewState } from '../api'
import { useLoad } from '../useLoad'
import { Loading } from './common'

interface Dash {
  current_day: number
  current: {
    day: number; title: string; goals: string[]; phase: number; phase_title: string; minutes: number
    available: boolean; why: string; kps: { name: string; level: Level }[]; state: DayState
  } | null
  completed_days: number
  study_dates: number
  review: ReviewState
  wrong_open: number
  interview_pending: number
  projects: { next: { id: string; name: string; minutes: number; project: string } | null; behind: number; done: number; total: number }
  ability: { learned: number; mastered: number; total_kps: number; objective_accuracy: number | null; interview_score: number | null; categories: Record<string, number | null> }
  exams: { phase: number; title: string; available: boolean; why: string; passed: boolean; best: number | null }[]
  roadmap: { day: number; phase: number; title: string; status: string; best: number | null }[]
  pass_score: number
  content_errors: number
}

export default function Dashboard() {
  const { data, error } = useLoad<Dash>('/api/dashboard')
  const nav = useNavigate()
  if (!data) return <Loading error={error} />
  const cur = data.current
  const st = cur?.state
  const pct = Math.round((data.completed_days / 50) * 100)
  const exam = data.exams.find((e) => e.available && !e.passed)

  const steps: [string, boolean, string][] = st
    ? [
        ['复习', st.done.review, data.review.needed ? `${data.review.size} 题${data.review.gap > 1 ? `（隔了 ${data.review.gap} 天）` : ''}` : data.review.done ? '已完成' : '今天不需要'],
        ['讲解', st.done.lesson, `${st.learned.length}/${cur!.kps.length} 个知识点`],
        ['当天测试', st.done.test, st.done.test ? `最高 ${fmtScore(st.best_score)} 分` : `12 题，≥${data.pass_score} 分解锁下一天`],
        ['面试 3 题', st.done.interview, `${st.interview_done}/${st.interview_total}，碎片时间完成`],
      ]
    : []

  return (
    <>
      {data.content_errors > 0 && (
        <div className="banner">有 {data.content_errors} 个课程内容文件校验未通过，对应天数暂不可学。详情见 <Link to="/settings">数据与设置</Link>。</div>
      )}
      <div className="card hero">
        <div>
          <div className="eyebrow">Day {pad(data.current_day)} / 50 · 第 {cur?.phase} 阶段 {cur?.phase_title}</div>
          <div className="title">{cur?.title ?? '课程内容缺失'}</div>
          {cur && (
            <div className="muted">
              {cur.kps.length} 个知识点 · 建议 {cur.minutes} 分钟
              {data.review.needed ? <> · <b>先复习 {data.review.size} 题</b></> : null}
            </div>
          )}
          {cur && !cur.available && <div className="small" style={{ marginTop: 4 }}>🔒 {cur.why}</div>}
        </div>
        {exam && cur && !cur.available ? (
          <button className="btn primary big" onClick={() => nav('/exams')}>去考第 {exam.phase} 阶段卷 →</button>
        ) : (
          <button className="btn primary big" disabled={!cur?.available} onClick={() => nav(`/day/${data.current_day}`)}>
            {data.review.needed ? '先复习，再学习 →' : st?.started ? '继续学习 →' : '开始今天的学习 →'}
          </button>
        )}
      </div>

      <div className="grid g4 mt">
        <div className="card stat">
          <div className="lbl">总进度</div>
          <div className="num">{data.completed_days} / 50 天</div>
          <div className="bar"><i style={{ width: pct + '%' }} /></div>
          <div className="small">已学习 {data.study_dates} 个日子</div>
        </div>
        <div className="card stat">
          <div className="lbl">基本掌握的知识点</div>
          <div className="num">{data.ability.mastered} / {data.ability.total_kps}</div>
          <div className="small">已学 {data.ability.learned}；隔天复习还能答对才算掌握</div>
        </div>
        <Link to="/review" className="card stat linkcard">
          <div className="lbl">错题 / 待写面试题</div>
          <div className="num">{data.wrong_open} / {data.interview_pending}</div>
          <div className="small">选择题正确率 {fmtScore(data.ability.objective_accuracy)}%</div>
        </Link>
        <Link to="/projects" className="card stat linkcard">
          <div className="lbl">项目</div>
          <div className="num">{data.projects.done} / {data.projects.total} 模块</div>
          <div className="small">
            {data.projects.next ? `下一步：${data.projects.next.name}${data.projects.behind > 1 ? `（落后 ${data.projects.behind} 个）` : ''}` : '暂无可做的模块'}
          </div>
        </Link>
      </div>

      <div className="grid g2 mt">
        <div className="card">
          <h3>今天的流程</h3>
          {steps.map(([name, done, desc], i) => (
            <div className="task" key={name}>
              <div className={'dot' + (done ? ' done' : st?.stage === ['review', 'lesson', 'test', 'interview'][i] ? ' on' : '')}>{done ? '✓' : i + 1}</div>
              <div className="t">{name}</div>
              <div className="small">{desc}</div>
            </div>
          ))}
          <div className="small mt">只有 1 小时：复习 + 讲解 + 测试就够了。面试题和项目放到有空的时候。</div>
        </div>
        <div className="card">
          <h3>阶段卷（满分 100）</h3>
          {data.exams.map((e) => (
            <div className="list-item" key={e.phase}>
              <span>第 {e.phase} 阶段 · {e.title}</span>
              {e.passed ? (
                <span className="pill ok">{fmtScore(e.best)} 分 · 已通过</span>
              ) : e.available ? (
                <Link to="/exams" className="pill warn">{e.best !== null ? `最高 ${fmtScore(e.best)}，` : ''}去考试</Link>
              ) : (
                <span className="small">Day {e.phase * 10} 后开放</span>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="card mt">
        <div className="between">
          <h3 style={{ margin: 0 }}>50 天路线</h3>
          <span className="small">绿＝通过　橙＝通过但最高分低于 80　蓝框＝当前　灰＝未解锁</span>
        </div>
        {[1, 2, 3, 4, 5].map((ph) => (
          <div key={ph}>
            <div className="phase-title">第 {ph} 阶段 · {data.exams[ph - 1]?.title}</div>
            <div className="cells">
              {data.roadmap.filter((r) => r.phase === ph).map((r) => {
                const open = r.status !== 'locked' && r.status !== 'missing'
                const body = (
                  <>
                    <b>Day {pad(r.day)}{r.best !== null ? ` · ${fmtScore(r.best)}` : ''}</b>
                    {r.title}
                  </>
                )
                return open ? (
                  <Link key={r.day} to={`/day/${r.day}`} className={'cell ' + r.status}>{body}</Link>
                ) : (
                  <div key={r.day} className={'cell ' + r.status}>{body}</div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {Object.values(data.ability.categories).some((v) => v !== null) && (
        <div className="card mt">
          <h3>各方向得分（全部作答平均）</h3>
          {Object.entries(data.ability.categories).filter(([, v]) => v !== null).map(([k, v]) => <ScoreBar key={k} name={CATEGORY_NAMES[k]} value={v} />)}
        </div>
      )}
    </>
  )
}

export function ScoreBar({ name, value }: { name: string; value: number | null | undefined }) {
  const v = value ?? 0
  const color = v >= 80 ? '#2b8a3e' : v >= 60 ? '#f08c00' : '#e03131'
  return (
    <div className="scorebar">
      <span className="name">{name}</span>
      <span className="track"><i style={{ width: `${v}%`, background: color }} /></span>
      <span className="val">{fmtScore(value)}</span>
    </div>
  )
}
