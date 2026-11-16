import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, fmtScore, pad, RESOURCE_KIND, type DailyReport, type DayDetail, type KnowledgePoint, type QuizSession, type Stage } from '../api'
import Markdown from '../components/Markdown'
import QuestionCard from '../components/QuestionCard'
import QuizRunner, { QuizResult } from '../components/QuizRunner'
import { useToast } from '../components/Toast'
import { useLoad } from '../useLoad'
import { Loading } from './common'

const STAGES: [Stage, string][] = [
  ['review', '复习'],
  ['lesson', '讲解'],
  ['test', '当天测试'],
  ['interview', '面试 3 题'],
  ['summary', '总结'],
]

function useStageTimer(day: number, stage: Stage, active: boolean) {
  useEffect(() => {
    if (!active) return
    let acc = 0
    const tick = setInterval(() => {
      if (document.visibilityState === 'visible') acc += 5
    }, 5000)
    const flush = () => {
      if (acc > 0) {
        api.post(`/api/days/${day}/time`, { stage, seconds: acc }).catch(() => {})
        acc = 0
      }
    }
    const f = setInterval(flush, 60000)
    return () => {
      clearInterval(tick)
      clearInterval(f)
      flush()
    }
  }, [day, stage, active])
}

export default function Daily() {
  const n = Number(useParams().day)
  const { data, error, reload } = useLoad<DayDetail>(`/api/days/${n}`)
  const [view, setView] = useState<Stage | null>(null)

  useEffect(() => {
    setView(null)
  }, [n])

  const stage = view ?? data?.state.stage ?? 'lesson'
  useStageTimer(n, stage, !!data?.available)

  if (!data) return <Loading error={error} />
  if (!data.available) {
    return (
      <div className="card">
        <h2>Day {pad(n)} · {data.title}</h2>
        <p className="muted">🔒 {data.why}</p>
        <Link to="/" className="btn">返回驾驶舱</Link>
      </div>
    )
  }
  const st = data.state
  const minutes = Math.round(Object.values(st.seconds).reduce((a, b) => a + b, 0) / 60)
  const go = (s: Stage) => {
    setView(s)
    window.scrollTo(0, 0)
  }
  const progress: Record<Stage, string> = {
    review: st.review.needed ? `${st.review.size} 题` : st.review.done ? '已完成' : '今天不需要',
    lesson: `${st.learned.length}/${data.knowledge_points.length}`,
    test: st.completed ? `最高 ${fmtScore(st.best_score)}` : st.tests_taken ? `已测 ${st.tests_taken} 次` : '≥70 解锁',
    interview: `${st.interview_done}/${st.interview_total}`,
    summary: '',
  }

  return (
    <>
      <div className="between">
        <div>
          <div className="small">
            Day {pad(n)} / 50 · 第 {data.phase} 阶段 {data.phase_title} · 建议 {data.minutes} 分钟
            {minutes ? ` · 已学习约 ${minutes} 分钟` : ''}
          </div>
          <h1>{data.title}</h1>
        </div>
        {st.completed && <span className="pill ok">已通过 · {st.completed_at?.slice(0, 10)}</span>}
      </div>
      <div className="small">今日目标：{data.goals.join('；')}</div>

      <div className="stepper">
        {STAGES.map(([k, name]) => (
          <button key={k} className={'step' + (stage === k ? ' on' : st.done[k] ? ' done' : '')} onClick={() => go(k)}>
            <b>{st.done[k] && k !== 'summary' ? '✓ ' : ''}{name}</b>
            <span>{progress[k]}</span>
          </button>
        ))}
      </div>

      {stage === 'review' && <ReviewStage data={data} reload={reload} next={() => go('lesson')} />}
      {stage === 'lesson' && <Lesson data={data} reload={reload} next={() => go('test')} />}
      {stage === 'test' && <TestStage data={data} reload={reload} goto={go} />}
      {stage === 'interview' && <InterviewStage data={data} reload={reload} next={() => go('summary')} />}
      {stage === 'summary' && <Summary data={data} goto={go} />}
    </>
  )
}

// ---------- 复习 ----------

function useSession(id: number | null) {
  const [s, setS] = useState<QuizSession | null>(null)
  useEffect(() => {
    if (id) api.get<QuizSession>(`/api/sessions/${id}`).then(setS).catch(() => {})
  }, [id])
  return [s, setS] as const
}

function ReviewStage({ data, reload, next }: { data: DayDetail; reload: () => void; next: () => void }) {
  const rv = data.state.review
  const [s, setS] = useSession(rv.pending_id)
  const toast = useToast()

  async function start() {
    try {
      setS(await api.post<QuizSession>('/api/review/start'))
    } catch (e) {
      toast((e as Error).message)
    }
  }

  if (s?.submitted) {
    return (
      <>
        <QuizResult s={s} />
        <div className="pager">
          <span className="small">答错的题已进入错题本，相关知识点会更早再出现。</span>
          <button className="btn primary" onClick={async () => { await reload(); next() }}>复习完成，开始今天的讲解 →</button>
        </div>
      </>
    )
  }
  if (s) return <QuizRunner s={s} onSubmitted={setS} />
  if (!rv.needed) {
    return (
      <div className="card">
        <h3>{rv.done ? '今天的复习已完成 ✓' : '今天不需要复习'}</h3>
        <p className="muted">{rv.done ? '可以直接开始讲解。' : '还没有往日学过的知识点。从明天起，每次打开会先做一组复习题。'}</p>
        <button className="btn primary" onClick={next}>开始讲解 →</button>
      </div>
    )
  }
  return (
    <div className="card">
      <h3>先复习 {rv.size} 道题，再学新内容</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        {rv.gap > 1 ? `距上次学习已经 ${rv.gap} 天，题量相应增加。` : '距上次学习 1 天。'}
        题目优先来自：<b>错题</b> → <b>到期复习</b> → <b>掌握不扎实</b> → <b>很久没碰的旧知识</b>。全是选择题，约 {Math.ceil(rv.size * 0.6)} 分钟。
      </p>
      <button className="btn primary big" onClick={start}>开始复习</button>
    </div>
  )
}

// ---------- 讲解 ----------

const SECTIONS: [keyof KnowledgePoint, string][] = [
  ['analogy', '用前端经验理解'],
  ['why', '为什么要学'],
  ['problem', '它解决什么问题'],
  ['principle', '核心原理'],
  ['scenarios', '实际工作中怎么用'],
  ['code', '代码示例'],
  ['pitfalls', '常见错误和易混点'],
  ['project_example', '在项目里的样子'],
]

function Lesson({ data, reload, next }: { data: DayDetail; reload: () => void; next: () => void }) {
  const kps = data.knowledge_points
  const learned = new Set(data.state.learned)
  const [i, setI] = useState(() => {
    const idx = kps.findIndex((k) => !learned.has(k.id))
    return idx < 0 ? 0 : idx
  })
  const k = kps[i]
  const toast = useToast()
  const [note, setNote] = useState(k.note)
  useEffect(() => setNote(k.note), [k.id, k.note])

  if (data.state.review.needed) {
    return <div className="card locked-box">请先完成今天的复习，再学新内容。</div>
  }

  async function markAndNext() {
    try {
      if (!learned.has(k.id)) await api.post(`/api/days/${data.day}/learn`, { kp_id: k.id })
      await reload()
      if (i < kps.length - 1) {
        setI(i + 1)
        window.scrollTo(0, 0)
      } else next()
    } catch (e) {
      toast((e as Error).message)
    }
  }
  async function saveNote() {
    if (note === k.note) return
    await api.put(`/api/kps/${k.id}`, { note }).then(() => toast('笔记已保存', 'ok')).catch((e) => toast(e.message))
  }
  async function toggleOutdated() {
    await api.put(`/api/kps/${k.id}`, { outdated: !k.outdated }).then(reload).catch((e) => toast(e.message))
  }

  return (
    <>
      {i === 0 && data.resources.length > 0 && (
        <div className="card">
          <h3>配套资源（可选，有时间再看）</h3>
          {data.resources.map((r) => (
            <div className="list-item" key={r.url}>
              <span>
                <span className="pill">{RESOURCE_KIND[r.kind]}{r.lang === 'en' ? ' · 英文' : ''}{r.minutes ? ` · ${r.minutes} 分钟` : ''}</span>{' '}
                <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a>
                <div className="small">{r.note}</div>
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="card lesson mt">
        <div className="kp-nav">
          {kps.map((x, j) => (
            <button key={x.id} className={(j === i ? 'on ' : '') + (learned.has(x.id) ? 'ok' : '')} onClick={() => setI(j)}>{x.name}</button>
          ))}
        </div>
        <h2>
          <span className={'tag ' + k.level.toLowerCase()}>{k.level}</span>
          {k.name}
          <span className="small" style={{ marginLeft: 10, fontWeight: 400 }}>
            {i + 1}/{kps.length} · {k.level === 'P0' ? '必须掌握' : k.level === 'P1' ? '理解原理和场景' : '了解即可'} · 当前：{k.mastery_name}
          </span>
        </h2>
        <div className="memo"><b>一句话记住：</b>{k.summary}</div>
        {SECTIONS.map(([f, title]) =>
          k[f] ? (
            <section key={f} className={f === 'analogy' ? 'analogy' : ''}>
              <h4>{title}</h4>
              <Markdown>{k[f] as string}</Markdown>
            </section>
          ) : null,
        )}
        <section>
          <h4>面试官可能这样问</h4>
          {k.interview_asks.map((item, j) => {
            const q = typeof item === 'string' ? item : item.question
            const a = typeof item === 'string' ? '' : item.answer
            return (
              <div className="ask" key={j}>
                <div className="ask-q">{j + 1}. {q}</div>
                {a ? <div className="ask-a"><b>可以这样答：</b>{a}</div> : null}
              </div>
            )
          })}
        </section>
        {(k.freshness || k.sources.length > 0) && (
          <div className="fresh">
            {k.freshness && <Markdown>{'**资料时效：**' + k.freshness}</Markdown>}
            {k.sources.length > 0 && (
              <div className="small" style={{ marginTop: 4 }}>
                参考资料：{k.sources.map((s, j) => <span key={s.url}>{j ? '；' : ''}<a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></span>)}
              </div>
            )}
          </div>
        )}
        <section className="note">
          <h4>我的笔记</h4>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} onBlur={saveNote} placeholder="可选：用自己的话记一两句（离开输入框自动保存）" />
        </section>
        <div className="pager">
          <button className="btn ghost" onClick={toggleOutdated} title="发现内容过时或有误时标记，之后在「数据与设置」里集中查看">
            {k.outdated ? '已标记过时（点击取消）' : '标记内容过时/有误'}
          </button>
          <div className="row">
            {i > 0 && <button className="btn" onClick={() => setI(i - 1)}>上一个</button>}
            <button className="btn primary" onClick={markAndNext}>
              {i < kps.length - 1 ? '读完了，下一个知识点' : '读完了，去做当天测试 →'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

// ---------- 当天测试 ----------

function TestStage({ data, reload, goto }: { data: DayDetail; reload: () => void; goto: (s: Stage) => void }) {
  const st = data.state
  const [s, setS] = useSession(st.pending_test)
  const [busy, setBusy] = useState(false)
  const toast = useToast()

  async function start() {
    setBusy(true)
    try {
      setS(await api.post<QuizSession>(`/api/days/${data.day}/test`))
      window.scrollTo(0, 0)
    } catch (e) {
      toast((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  async function onSubmitted(r: QuizSession) {
    setS(r)
    await reload()
  }

  if (!st.done.review || !st.done.lesson) {
    return <div className="card locked-box">{!st.done.review ? '请先完成今天的复习。' : '读完今天的全部知识点后开始测试。'}</div>
  }
  if (s?.submitted) {
    const weak = s.result?.weak ?? []
    return (
      <>
        <QuizResult s={s} />
        <div className="card mt">
          {s.passed ? (
            <div className="between">
              <span>✓ 通过，Day {pad(data.day + 1)} 已解锁。今天的 3 道面试题可以在碎片时间里慢慢写。</span>
              <button className="btn primary" onClick={() => goto('interview')}>去做面试题 →</button>
            </div>
          ) : (
            <>
              <div>
                没到 70 分。{weak.length ? <>建议先回看：<b>{weak.map((k) => k.name).join('、')}</b>。</> : null}
                重测会换一批题，并多出错得多的知识点。
              </div>
              <div className="row mt">
                <button className="btn" onClick={() => goto('lesson')}>回看讲解</button>
                <button className="btn primary" disabled={busy} onClick={start}>重新测试</button>
              </div>
            </>
          )}
        </div>
      </>
    )
  }
  if (s) return <QuizRunner s={s} onSubmitted={onSubmitted} />
  return (
    <div className="card">
      <h3>{st.completed ? `当天测试已通过（最高 ${fmtScore(st.best_score)} 分）` : '当天测试'}</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        从 {data.test_pool} 道题里抽 12 道选择/判断题，每个知识点至少 3 道，含读代码题。<b>≥70 分</b>解锁下一天；没过可以重测，每次换题。
      </p>
      <button className="btn primary big" disabled={busy} onClick={start}>{st.completed ? '再测一次巩固' : st.tests_taken ? '重新测试' : '开始测试'}</button>
    </div>
  )
}

// ---------- 面试 3 题 ----------

function InterviewStage({ data, reload, next }: { data: DayDetail; reload: () => void; next: () => void }) {
  const qs = data.interview
  const atts = data.interview_attempts
  const [i, setI] = useState(() => {
    const idx = qs.findIndex((q) => !atts[q.id])
    return idx < 0 ? 0 : idx
  })
  if (!data.state.completed) {
    return <div className="card locked-box">当天测试通过后开放面试题。</div>
  }
  const q = qs[i]
  return (
    <>
      <div className="small" style={{ marginBottom: 8 }}>
        面试官今天问你 3 道题（以场景题为主）。<b>不影响解锁</b>，可以分散在一天的碎片时间里写，草稿自动保存。写完对照要点自评。
      </div>
      <div className="qnav">
        {qs.map((x, j) => {
          const a = atts[x.id]
          return (
            <button key={x.id} className={(j === i ? 'on ' : '') + (a ? (a.score >= 80 ? 'good' : a.score >= 60 ? 'mid' : 'bad') : '')} onClick={() => setI(j)}>
              {j + 1}
            </button>
          )
        })}
      </div>
      <QuestionCard key={q.id} q={q} context="interview" existing={atts[q.id]} onDone={() => reload()} />
      <div className="pager">
        <span className="small">第 {i + 1} / {qs.length} 题</span>
        <div className="row">
          {i > 0 && <button className="btn" onClick={() => setI(i - 1)}>上一题</button>}
          {i < qs.length - 1 ? (
            <button className="btn primary" onClick={() => { setI(i + 1); window.scrollTo(0, 0) }}>下一题</button>
          ) : (
            <button className="btn primary" onClick={next}>看今日总结 →</button>
          )}
        </div>
      </div>
    </>
  )
}

// ---------- 总结 ----------

function Summary({ data, goto }: { data: DayDetail; goto: (s: Stage) => void }) {
  const nav = useNavigate()
  if (!data.report) {
    return (
      <div className="card">
        <h3>当天测试通过后生成总结</h3>
        <button className="btn primary" onClick={() => goto('test')}>去测试</button>
      </div>
    )
  }
  const r = data.report
  return (
    <>
      <DailyReportView r={r} interviewDone={data.state.interview_done} />
      <div className="pager">
        <Link to="/" className="btn">返回驾驶舱</Link>
        <div className="row">
          {data.state.interview_done < data.state.interview_total && <button className="btn" onClick={() => goto('interview')}>继续写面试题</button>}
          {r.exam_next ? (
            <Link to="/exams" className="btn primary">去考第 {data.phase} 阶段卷</Link>
          ) : r.tomorrow ? (
            <button className="btn primary" onClick={() => nav(`/day/${data.day + 1}`)}>继续 Day {pad(data.day + 1)}</button>
          ) : null}
        </div>
      </div>
    </>
  )
}

export function DailyReportView({ r, interviewDone }: { r: DailyReport; interviewDone?: number }) {
  const ivDone = interviewDone ?? r.interview_done
  return (
    <div className="card">
      <div className="between">
        <h2 style={{ margin: 0 }}>Day {pad(r.day)} 总结 · {r.title}</h2>
        <span className="small">用时约 {r.minutes} 分钟</span>
      </div>
      <div className="grid g3 mt">
        <div><div className="small">当天测试</div><div className="stat"><span className="num">{fmtScore(r.test_score)}</span>{r.tests_taken > 1 && <span className="small"> 第 {r.tests_taken} 次通过</span>}</div></div>
        <div><div className="small">面试题</div><div className="stat"><span className="num">{ivDone}/{r.interview_total}</span></div></div>
        <div><div className="small">错题</div><div className="stat"><span className="num">{r.wrong.length}</span></div></div>
      </div>
      <div className="label">今日知识点</div>
      <table className="t">
        <thead><tr><th>知识点</th><th>测试得分</th><th>掌握程度</th><th>下次复习</th></tr></thead>
        <tbody>
          {r.kps.map((k) => (
            <tr key={k.id}>
              <td><span className={'tag ' + k.level.toLowerCase()}>{k.level}</span>{k.name}</td>
              <td className={(k.test_avg ?? 0) < 70 ? 'bad-text' : ''}>{fmtScore(k.test_avg)}</td>
              <td>{k.mastery_name}</td>
              <td>{k.next_review ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {r.weak.length > 0 && <div className="mt"><b>明天会重点复习：</b>{r.weak.join('、')}</div>}
      {r.projects.length > 0 && (
        <div className="mt">
          <b>项目新解锁：</b>
          {r.projects.map((p) => `${p.name}（约 ${p.minutes} 分钟）`).join('、')} · <Link to="/projects">去做项目</Link>
        </div>
      )}
      {r.tomorrow && (
        <div className="mt small">下一天：Day {pad(r.tomorrow.day)} · {r.tomorrow.title}</div>
      )}
      <div className="small mt">当天表现好只算「初步理解」，之后几天复习还能答对才会升级为「基本掌握」。</div>
    </div>
  )
}
