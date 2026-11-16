import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, pad, type Attempt, type Question } from '../api'
import Markdown from '../components/Markdown'
import QuestionCard, { fallbackCopy } from '../components/QuestionCard'
import { useToast } from '../components/Toast'
import { useLoad } from '../useLoad'
import { Loading } from './common'

type TestKind = 'functional' | 'api' | 'exception' | 'review'
interface Module {
  id: string
  name: string
  unlock_day: number
  minutes: number
  features: string[]
  goal: string
  design: string
  data_flow: string
  key_code: string
  ai_prompt: string
  tests: Record<TestKind, string[]>
  retell: Question
  status: { checks: Partial<Record<TestKind, number[]>>; note: string; done: number; total: number; retell: Attempt | null; unlocked: boolean; completed: boolean }
}
interface ProjectData {
  id: string
  title: string
  role: string
  intro: string
  market: string
  tech_stack: string
  architecture: string
  resume: string
  materials: { architecture_doc: string; deployment: string; interview_pitch: string }
  modules: Module[]
  deep_dive_count: number
}
interface ProjectRow { id: string; title: string; role: string; done: number; unlocked: number; total: number; first_day: number }

const TEST_NAMES: Record<TestKind, string> = { functional: '功能', api: '接口', exception: '异常', review: '代码审查' }

export default function Projects() {
  const { pid = 'p1', tab = 'overview' } = useParams()
  const list = useLoad<ProjectRow[]>('/api/projects')
  const nav = useNavigate()
  return (
    <>
      <h1>实践项目</h1>
      <div className="small" style={{ marginBottom: 12 }}>
        3 个项目跟着课程进度逐个模块解锁，只在工作日做。可以让 AI 写大部分代码，但每个模块都要<b>勾完验收清单 + 复述原理 ≥60 分</b>才算完成——面试官会深挖。
      </div>
      <div className="tabs">
        {(list.data ?? []).map((p) => (
          <button key={p.id} className={pid === p.id ? 'on' : ''} onClick={() => nav(`/projects/${p.id}`)}>
            {p.title} <span className="small">{p.done}/{p.total}{p.unlocked === 0 ? ` · Day ${pad(p.first_day)} 起` : ''}</span>
          </button>
        ))}
      </div>
      {list.error && <Loading error={list.error} />}
      <ProjectView key={pid} pid={pid} tab={tab} onChange={list.reload} />
    </>
  )
}

function ProjectView({ pid, tab, onChange }: { pid: string; tab: string; onChange: () => void }) {
  const { data, error, reload } = useLoad<ProjectData>(`/api/projects/${pid}`)
  const nav = useNavigate()
  if (!data) return <Loading error={error} />
  const go = (t: string) => {
    nav(`/projects/${pid}/${t}`)
    window.scrollTo(0, 0)
  }
  const m = data.modules.find((x) => x.id === tab)
  return (
    <div className="split">
      <div className="side-list">
        <button className={tab === 'overview' ? 'on' : ''} onClick={() => go('overview')}>项目概览</button>
        {data.modules.map((x) => (
          <button key={x.id} className={(tab === x.id ? 'on ' : '') + (x.status.unlocked ? '' : 'locked')} onClick={() => go(x.id)}>
            {x.status.completed ? '✓ ' : x.status.unlocked ? '' : '🔒 '}{x.name}
            <span className="small">Day {pad(x.unlock_day)} · {x.minutes} 分钟</span>
          </button>
        ))}
        <button className={tab === 'materials' ? 'on' : ''} onClick={() => go('materials')}>交付与面试材料</button>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {tab === 'overview' && <Overview p={data} />}
        {tab === 'materials' && <Materials m={data.materials} />}
        {m && <ModuleView key={m.id} m={m} reload={async () => { await reload(); onChange() }} />}
      </div>
    </div>
  )
}

function Overview({ p }: { p: ProjectData }) {
  return (
    <div className="card lesson">
      <h2>{p.title} <span className="small">对应岗位：{p.role}</span></h2>
      <Markdown>{p.intro}</Markdown>
      <section><h4>为什么做这个项目（市场与 JD）</h4><Markdown>{p.market}</Markdown></section>
      <section><h4>技术栈</h4><Markdown>{p.tech_stack}</Markdown></section>
      <section><h4>整体架构</h4><Markdown>{p.architecture}</Markdown></section>
      <section><h4>简历写法</h4><Markdown>{p.resume}</Markdown></section>
      <div className="small mt">
        做完第一个模块后，可以在 <Link to="/mock">模拟面试</Link> 里做这个项目的深挖面试（题库 {p.deep_dive_count} 题）。
      </div>
    </div>
  )
}

function ModuleView({ m, reload }: { m: Module; reload: () => Promise<void> }) {
  const toast = useToast()
  const [note, setNote] = useState(m.status.note)
  const locked = !m.status.unlocked
  async function save(checks?: Module['status']['checks'], n?: string) {
    try {
      await api.put(`/api/projects/module/${m.id}`, { checks: checks ?? m.status.checks, note: n ?? note })
      await reload()
    } catch (e) {
      toast((e as Error).message)
    }
  }
  function toggle(kind: TestKind, i: number) {
    const cur = new Set(m.status.checks[kind] ?? [])
    if (cur.has(i)) cur.delete(i)
    else cur.add(i)
    save({ ...m.status.checks, [kind]: [...cur] })
  }
  function copyPrompt() {
    const ok = () => toast('需求说明已复制，粘贴给 Cursor 等 AI 编程工具', 'ok')
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(m.ai_prompt).then(ok, () => fallbackCopy(m.ai_prompt, ok))
    else fallbackCopy(m.ai_prompt, ok)
  }
  return (
    <>
      {locked && <div className="banner">学到 Day {pad(m.unlock_day)} 后解锁。现在可以先浏览，但还不能勾选验收。</div>}
      {m.status.completed && <div className="banner ok">✓ 这个模块已完成</div>}
      <div className="card lesson">
        <h2>{m.name} <span className="small">约 {m.minutes} 分钟</span></h2>
        <div className="small">覆盖功能：{m.features.join('、')}</div>
        <section><h4>目标</h4><Markdown>{m.goal}</Markdown></section>
        <section><h4>设计要点与技术决策</h4><Markdown>{m.design}</Markdown></section>
        <section><h4>数据流</h4><Markdown>{m.data_flow}</Markdown></section>
        <section><h4>必须读懂的关键代码</h4><Markdown>{m.key_code}</Markdown></section>
        <section>
          <div className="between">
            <h4 style={{ margin: 0 }}>交给 AI 编程工具的需求说明</h4>
            <button className="btn ghost" onClick={copyPrompt}>复制</button>
          </div>
          <details className="ref">
            <summary>展开查看</summary>
            <Markdown>{m.ai_prompt}</Markdown>
          </details>
        </section>
      </div>
      <div className="card mt">
        <h3>验收清单 <span className="small">{m.status.done}/{m.status.total}</span></h3>
        <div className="grid g2">
          {(Object.keys(TEST_NAMES) as TestKind[]).map((k) => (
            <div key={k}>
              <div className="label">{TEST_NAMES[k]}</div>
              {m.tests[k].map((t, i) => (
                <label className="checkline" key={i}>
                  <input type="checkbox" disabled={locked} checked={(m.status.checks[k] ?? []).includes(i)} onChange={() => toggle(k, i)} />
                  <span><Markdown>{t}</Markdown></span>
                </label>
              ))}
            </div>
          ))}
        </div>
        <div className="label">实现记录（遇到的问题、做的决策——面试时最好用的素材）</div>
        <textarea style={{ width: '100%', minHeight: 80 }} disabled={locked} value={note} onChange={(e) => setNote(e.target.value)} onBlur={() => note !== m.status.note && save(undefined, note)} />
      </div>
      {!locked && (
        <div className="mt">
          <div className="label">复述原理（≥60 分且清单全部勾完，模块才算完成）</div>
          <QuestionCard q={m.retell} context="project" existing={m.status.retell} onDone={() => save()} />
        </div>
      )}
    </>
  )
}

function Materials({ m }: { m: ProjectData['materials'] }) {
  const [t, setT] = useState<keyof ProjectData['materials']>('architecture_doc')
  const names = { architecture_doc: '架构说明', deployment: '部署说明', interview_pitch: '面试讲解稿' }
  return (
    <div className="card lesson">
      <div className="tabs">
        {(Object.keys(names) as (keyof typeof names)[]).map((k) => (
          <button key={k} className={t === k ? 'on' : ''} onClick={() => setT(k)}>{names[k]}</button>
        ))}
      </div>
      <Markdown>{m[t]}</Markdown>
    </div>
  )
}
