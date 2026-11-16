import { useEffect, useRef, useState } from 'react'
import { api, DIM_NAMES, OBJECTIVE, pad, TYPE_NAMES, type Attempt, type AttemptResult, type ObjAnswer, type Question } from '../api'
import Markdown, { CodeBlock } from './Markdown'
import { useToast } from './Toast'

const CHECK_LABELS: [number, string][] = [
  [0, '没说到'],
  [0.5, '部分'],
  [1, '说到了'],
]
const EXPR_LABELS = ['', '卡壳混乱', '零散', '基本清楚', '清楚有条理', '结论先行、层次分明']

interface Props {
  q: Question
  context: string
  sessionId?: number
  existing?: Attempt | null
  presetAnswer?: string
  allowRetry?: boolean
  onDone?: (r: AttemptResult) => void
}

/** 单题作答：面试题、错题重做、项目复述、模拟面试。整组交卷的题（复习/测试/阶段卷）用 QuizRunner。 */
export default function QuestionCard(props: Props) {
  const { q, context, sessionId, existing, presetAnswer, allowRetry = true, onDone } = props
  const objective = OBJECTIVE.includes(q.type)
  const draftKey = `${context}${sessionId ?? ''}:${q.id}`
  const toast = useToast()

  const [retry, setRetry] = useState(false)
  const [phase, setPhase] = useState<'answer' | 'grade'>(presetAnswer !== undefined ? 'grade' : 'answer')
  const [text, setText] = useState(presetAnswer ?? '')
  const [pick, setPick] = useState<ObjAnswer | null>(null)
  const [checks, setChecks] = useState<(number | null)[]>(() => (q.key_points ?? []).map(() => null))
  const [expr, setExpr] = useState<number | null>(null)
  const [result, setResult] = useState<{ r: AttemptResult; a: Partial<Attempt>; pick: ObjAnswer | null } | null>(null)
  const [busy, setBusy] = useState(false)
  const saveTimer = useRef<number | undefined>(undefined)
  const needExpr = q.type === 'oral' || q.type === 'design' || !!q.oral

  function reset() {
    setPhase(presetAnswer !== undefined ? 'grade' : 'answer')
    setText(presetAnswer ?? '')
    setPick(null)
    setChecks((q.key_points ?? []).map(() => null))
    setExpr(null)
    setResult(null)
  }
  useEffect(() => {
    setRetry(false)
    reset()
  }, [q.id, presetAnswer]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (objective || presetAnswer !== undefined) return
    let alive = true
    api.get<{ text: string }>(`/api/drafts/${encodeURIComponent(draftKey)}`).then((d) => {
      if (alive && d.text) setText((t) => t || d.text)
    }).catch(() => {})
    return () => {
      alive = false
    }
  }, [draftKey, objective, presetAnswer])

  function onText(v: string) {
    setText(v)
    window.clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => {
      api.put(`/api/drafts/${encodeURIComponent(draftKey)}`, { text: v }).catch(() => {})
    }, 600)
  }

  async function submit(body: Record<string, unknown>) {
    setBusy(true)
    try {
      const r = await api.post<AttemptResult>('/api/attempts', { question_id: q.id, context, session_id: sessionId, ...body })
      setResult({ r, a: { answer: typeof body.answer === 'string' ? body.answer : '', checks: (body.checks as number[]) ?? null, gave_up: !!body.gave_up }, pick })
      setRetry(false)
      onDone?.(r)
    } catch (e) {
      toast((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const done = result
    ? { score: result.r.score, answer: result.a.answer ?? '', checks: result.a.checks ?? null, gave_up: !!result.a.gave_up, dims: result.r.dims }
    : existing && !retry
      ? { score: existing.score, answer: existing.answer, checks: existing.checks, gave_up: existing.gave_up, dims: existing.dims }
      : null
  const shown: Question = result?.r.answer !== undefined ? { ...q, answer: result.r.answer, explain: result.r.explain ?? q.explain } : q

  return (
    <div className="qcard">
      <QHead q={q} />
      <QBody q={q} />

      {done ? (
        objective ? (
          <ObjectiveReveal q={shown} picked={result?.pick ?? null} score={done.score} />
        ) : (
          <SubjectiveDone q={q} done={done} />
        )
      ) : objective ? (
        <ObjectiveInput q={q} value={pick} onChange={setPick} />
      ) : phase === 'answer' ? (
        <>
          <textarea
            className="answer"
            value={text}
            placeholder="先用自己的话写下回答（像面试时说出来那样，写要点也可以）。写完再看评分要点。"
            onChange={(e) => onText(e.target.value)}
          />
          <div className="small">草稿自动保存，可以分几次写完。</div>
        </>
      ) : (
        <GradeView q={q} text={text} checks={checks} setChecks={setChecks} needExpr={needExpr} expr={expr} setExpr={setExpr} />
      )}

      <div className="qactions">
        {done ? (
          <>
            {!objective && <CopyForAI q={q} answer={done.answer} />}
            {allowRetry && (
              <button className="btn ghost" onClick={() => { setRetry(true); reset() }}>再答一次</button>
            )}
          </>
        ) : objective ? (
          <>
            <button className="btn ghost" disabled={busy} onClick={() => submit({ gave_up: true })}>不会，看答案</button>
            <button className="btn primary" disabled={busy || isEmpty(pick)} onClick={() => submit({ answer: pick })}>提交</button>
          </>
        ) : phase === 'answer' ? (
          <>
            <button className="btn ghost" disabled={busy} onClick={() => submit({ gave_up: true, answer: text, expression: needExpr ? 1 : undefined })}>
              不会，看答案
            </button>
            <button className="btn primary" disabled={!text.trim()} onClick={() => setPhase('grade')}>写好了，对照要点自评</button>
          </>
        ) : (
          <>
            {presetAnswer === undefined && <button className="btn ghost" onClick={() => setPhase('answer')}>返回修改</button>}
            {!text.trim() && (
              <button className="btn ghost" disabled={busy} onClick={() => submit({ gave_up: true, answer: '', expression: needExpr ? 1 : undefined })}>没作答，记 0 分</button>
            )}
            <button
              className="btn primary"
              disabled={busy || !text.trim() || checks.some((c) => c === null) || (needExpr && expr === null)}
              onClick={() => submit({ answer: text, checks, expression: needExpr ? expr : undefined })}
            >
              确认自评
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export function isEmpty(v: ObjAnswer | null | undefined) {
  return v === null || v === undefined || (Array.isArray(v) && v.length === 0)
}

export function QHead({ q, extra }: { q: Question; extra?: React.ReactNode }) {
  return (
    <div className="qhead">
      <span className="qtype">{TYPE_NAMES[q.type]}</span>
      {q.difficulty ? <span className="small">难度 {'●'.repeat(q.difficulty)}{'○'.repeat(4 - q.difficulty)}</span> : null}
      {q.kp_name ? (
        <span className="small">
          {q.kp_level ? <span className={'tag ' + q.kp_level.toLowerCase()}>{q.kp_level}</span> : null}
          {q.kp_name}
          {q.day ? ` · Day ${pad(q.day)}` : ''}
        </span>
      ) : null}
      {extra}
    </div>
  )
}

export function QBody({ q }: { q: Question }) {
  return (
    <>
      <div className="qtext"><Markdown>{q.question}</Markdown></div>
      {q.code && <CodeBlock code={q.code} language={q.lang} />}
    </>
  )
}

const letter = (i: number) => String.fromCharCode(65 + i)

export function ObjectiveInput({ q, value, onChange }: { q: Question; value: ObjAnswer | null | undefined; onChange: (v: ObjAnswer | null) => void }) {
  if (q.type === 'judge') {
    return (
      <div className="options row">
        <button className={'opt' + (value === true ? ' on' : '')} onClick={() => onChange(true)}>✓ 正确</button>
        <button className={'opt' + (value === false ? ' on' : '')} onClick={() => onChange(false)}>✗ 错误</button>
      </div>
    )
  }
  const picked = Array.isArray(value) ? value : []
  return (
    <div className="options">
      {q.type === 'multi' && <div className="small">多选：选出所有正确项（少选得一半分，错选不得分）</div>}
      {(q.options ?? []).map((o, i) => {
        const on = picked.includes(i)
        const next = q.type === 'multi' ? (on ? picked.filter((x) => x !== i) : [...picked, i].sort()) : [i]
        return (
          <button key={i} className={'opt' + (on ? ' on' : '')} onClick={() => onChange(next.length ? next : null)}>
            <b>{letter(i)}</b> <Markdown>{o}</Markdown>
          </button>
        )
      })}
    </div>
  )
}

export function answerText(a: ObjAnswer | null | undefined) {
  if (a === null || a === undefined) return '未作答'
  if (typeof a === 'boolean') return a ? '正确' : '错误'
  return a.map(letter).join('、') || '未作答'
}

export function ObjectiveReveal({ q, picked, score }: { q: Question; picked: ObjAnswer | null; score: number }) {
  const right = q.answer
  const cls = score >= 100 ? 'good' : score > 0 ? 'mid' : 'bad'
  const mine = Array.isArray(picked) ? picked : []
  return (
    <div className="done">
      <div className={'verdict ' + cls}>
        {picked === null ? '未作答' : score >= 100 ? '回答正确' : score > 0 ? '部分正确（少选）' : '回答错误'}
        <span className="small"> · 正确答案：{answerText(right)}{picked !== null ? ` · 你的答案：${answerText(picked)}` : ''}</span>
      </div>
      {q.options && (
        <div className="options">
          {q.options.map((o, i) => {
            const isRight = Array.isArray(right) && right.includes(i)
            const isMineWrong = mine.includes(i) && !isRight
            return (
              <div key={i} className={'opt static' + (isRight ? ' right' : isMineWrong ? ' wrongpick' : '')}>
                <b>{letter(i)}</b> <Markdown>{o}</Markdown>
              </div>
            )
          })}
        </div>
      )}
      <div className="explain">
        <div className="label">解析</div>
        <Markdown>{q.explain}</Markdown>
      </div>
    </div>
  )
}

function GradeView({ q, text, checks, setChecks, needExpr, expr, setExpr }: { q: Question; text: string; checks: (number | null)[]; setChecks: (v: (number | null)[]) => void; needExpr: boolean; expr: number | null; setExpr: (v: number) => void }) {
  return (
    <div className="grade">
      <div className="mine">
        <div className="label">我的回答</div>
        <div className="pre-wrap">{text || '（未作答）'}</div>
      </div>
      <div className="label">对照评分要点逐条自评（要诚实：说得含糊算「部分」）</div>
      {(q.key_points ?? []).map((kp, i) => (
        <div className="kpcheck" key={i}>
          <div><span className="dim">{DIM_NAMES[kp.dim]}</span> {kp.text}</div>
          <div className="seg">
            {CHECK_LABELS.map(([v, l]) => (
              <button key={v} className={checks[i] === v ? 'on v' + String(v).replace('.', '') : ''} onClick={() => setChecks(checks.map((c, j) => (j === i ? v : c)))}>
                {l}
              </button>
            ))}
          </div>
        </div>
      ))}
      {needExpr && (
        <div className="kpcheck">
          <div><span className="dim">表达</span> 如果是在面试中说出来，清晰程度如何？</div>
          <div className="seg">
            {[1, 2, 3, 4, 5].map((v) => (
              <button key={v} title={EXPR_LABELS[v]} className={expr === v ? 'on v1' : ''} onClick={() => setExpr(v)}>{v}</button>
            ))}
          </div>
        </div>
      )}
      <details className="ref" open>
        <summary>参考答案</summary>
        <Markdown>{q.reference}</Markdown>
      </details>
      {q.oral && (
        <details className="ref">
          <summary>面试口头表达版</summary>
          <Markdown>{q.oral}</Markdown>
        </details>
      )}
    </div>
  )
}

function SubjectiveDone({ q, done }: { q: Question; done: { score: number; answer: string; checks: number[] | null; gave_up: boolean; dims: Record<string, number> | null } }) {
  const cls = done.score >= 80 ? 'good' : done.score >= 60 ? 'mid' : 'bad'
  return (
    <div className="done">
      <div className={'verdict ' + cls}>
        自评 {Math.round(done.score)} 分{done.gave_up ? '（选择了看答案）' : ''}
        {done.dims && (
          <span className="dims">
            {Object.entries(done.dims).map(([k, v]) => <span key={k}>{DIM_NAMES[k] ?? k} {v}</span>)}
          </span>
        )}
      </div>
      {done.answer && (
        <div className="mine">
          <div className="label">我的回答</div>
          <div className="pre-wrap">{done.answer}</div>
        </div>
      )}
      <div className="label">评分要点</div>
      <ul className="kplist">
        {(q.key_points ?? []).map((kp, i) => {
          const c = done.checks?.[i]
          return (
            <li key={i} className={c === 1 ? 'hit' : c === 0.5 ? 'half' : 'miss'}>
              <span className="mark">{c === 1 ? '✓' : c === 0.5 ? '½' : '✗'}</span>
              <span className="dim">{DIM_NAMES[kp.dim]}</span> {kp.text}
            </li>
          )
        })}
      </ul>
      <details className="ref">
        <summary>参考答案</summary>
        <Markdown>{q.reference}</Markdown>
      </details>
      {q.oral && (
        <details className="ref">
          <summary>面试口头表达版</summary>
          <Markdown>{q.oral}</Markdown>
        </details>
      )}
    </div>
  )
}

function CopyForAI({ q, answer }: { q: Question; answer: string }) {
  const toast = useToast()
  function copy() {
    const kps = (q.key_points ?? []).map((k, i) => `${i + 1}. [${DIM_NAMES[k.dim]}] ${k.text}`).join('\n')
    const text = `你是一位严格的「AI 应用开发 / AI Agent 开发」岗位技术面试官。请评价我的回答，不要客套，不要因为鼓励而抬高分数。

【题目】
${q.question}${q.code ? '\n\n```' + q.lang + '\n' + q.code + '\n```' : ''}

【我的回答】
${answer || '（未作答）'}

【评分要点】
${kps}

【参考答案】
${q.reference ?? ''}

请按以下格式输出：
1. 正确点：具体指出我说对了什么
2. 错误点：指出说错的地方，并解释为什么错
3. 遗漏点：参考要点中我没有提到或说得含糊的
4. 评分：概念 / 原理 / 结合项目 / 工程思维 / 表达，各 1~5 分，并给出 0~100 总分
5. 一个追问，用来确认我是否真正理解
6. 一版更好的、适合面试口头表达的回答（1~2 分钟）`
    const ok = () => toast('已复制，可粘贴到 Cursor 或其他 AI 对话中获取严格评审', 'ok')
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(ok, () => fallbackCopy(text, ok))
    } else {
      fallbackCopy(text, ok)
    }
  }
  return (
    <button className="btn ghost" onClick={copy} title="系统本身不调用 AI；需要更严格的评价时，可把题目、你的回答和要点复制给 AI">
      复制给 AI 评审
    </button>
  )
}

export function fallbackCopy(text: string, done: () => void) {
  const ta = document.createElement('textarea')
  ta.value = text
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  ta.remove()
  done()
}
