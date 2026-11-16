import { useEffect, useState } from 'react'
import { api, fmtScore, pad, TYPE_NAMES, type ObjAnswer, type QuizSession } from '../api'
import { isEmpty, ObjectiveInput, ObjectiveReveal, QBody, QHead } from './QuestionCard'
import { useToast } from './Toast'

/** 整组作答、一次交卷：每日复习、当天测试、阶段卷。作答即时保存，中断后回来可以接着做。 */
export default function QuizRunner({ s, onSubmitted }: { s: QuizSession; onSubmitted: (s: QuizSession) => void }) {
  const [answers, setAnswers] = useState<Record<string, ObjAnswer>>(s.answers)
  const [i, setI] = useState(() => {
    const idx = s.questions.findIndex((q) => isEmpty(s.answers[q.id]))
    return idx < 0 ? 0 : idx
  })
  const [busy, setBusy] = useState(false)
  const toast = useToast()
  const q = s.questions[i]
  const answered = s.questions.filter((x) => !isEmpty(answers[x.id])).length

  useEffect(() => {
    setAnswers(s.answers)
  }, [s.id]) // eslint-disable-line react-hooks/exhaustive-deps

  function pick(v: ObjAnswer | null) {
    const next = { ...answers }
    if (v === null) delete next[q.id]
    else next[q.id] = v
    setAnswers(next)
    api.put(`/api/sessions/${s.id}/answer`, { question_id: q.id, answer: v }).catch((e) => toast(e.message))
    if (v !== null && q.type !== 'multi' && i < s.questions.length - 1) {
      window.setTimeout(() => setI((x) => (x === i ? i + 1 : x)), 350)
    }
  }

  async function submit() {
    const left = s.questions.length - answered
    if (!confirm(left ? `还有 ${left} 题没做（按 0 分计）。确定交卷？` : '确定交卷？交卷后显示答案和解析。')) return
    setBusy(true)
    try {
      onSubmitted(await api.post<QuizSession>(`/api/sessions/${s.id}/submit`))
      window.scrollTo(0, 0)
    } catch (e) {
      toast((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const reason = s.reasons?.[q.id]
  const pts = s.points?.[q.type]
  return (
    <div>
      <div className="qnav">
        {s.questions.map((x, j) => (
          <button key={x.id} className={(j === i ? 'on ' : '') + (!isEmpty(answers[x.id]) ? 'answered' : '')} onClick={() => setI(j)} title={TYPE_NAMES[x.type]}>
            {j + 1}
          </button>
        ))}
      </div>
      <div className="qcard">
        <QHead
          q={q}
          extra={
            <>
              {reason && <span className="pill warn">{reason}</span>}
              {pts && <span className="small">{pts} 分</span>}
            </>
          }
        />
        <QBody q={q} />
        <ObjectiveInput q={q} value={answers[q.id]} onChange={pick} />
      </div>
      <div className="pager">
        <span className="small">已答 {answered} / {s.questions.length} · 作答自动保存，可以随时离开再回来</span>
        <div className="row">
          {i > 0 && <button className="btn" onClick={() => setI(i - 1)}>上一题</button>}
          {i < s.questions.length - 1 && <button className="btn" onClick={() => setI(i + 1)}>下一题</button>}
          <button className={'btn' + (answered === s.questions.length ? ' primary' : '')} disabled={busy} onClick={submit}>交卷</button>
        </div>
      </div>
    </div>
  )
}

export function QuizResult({ s }: { s: QuizSession }) {
  const [onlyWrong, setOnlyWrong] = useState(true)
  const items = s.result?.items ?? {}
  const wrongCount = s.questions.filter((q) => (items[q.id]?.score ?? 0) < 100).length
  const list = s.questions.filter((q) => !onlyWrong || (items[q.id]?.score ?? 0) < 100)
  return (
    <>
      <div className="card">
        <div className="between">
          <div>
            <div className="small">{s.created_at.replace('T', ' ').slice(0, 16)} · 共 {s.questions.length} 题 · 错 {wrongCount} 题</div>
            <div className="bigscore">{fmtScore(s.score)}<span className="small"> / 100</span></div>
          </div>
          {s.kind !== 'review' && (s.passed ? <span className="pill ok">已通过（≥{s.pass_score}）</span> : <span className="pill bad">未通过（需 ≥{s.pass_score}）</span>)}
        </div>
        {s.result?.by_type && (
          <div className="row mt">
            {Object.entries(s.result.by_type).map(([t, v]) => (
              <span key={t} className="pill">{TYPE_NAMES[t]} {v.got}/{v.total}</span>
            ))}
          </div>
        )}
        {s.result?.kps && s.result.kps.length > 0 && (
          <>
            <div className="label">按知识点</div>
            <table className="t">
              <thead><tr><th>知识点</th><th>本次得分</th><th>当前掌握</th></tr></thead>
              <tbody>
                {s.result.kps.map((k) => (
                  <tr key={k.id}>
                    <td><span className={'tag ' + k.level.toLowerCase()}>{k.level}</span>Day {pad(k.day)} · {k.name}</td>
                    <td className={k.avg < 70 ? 'bad-text' : ''}>{fmtScore(k.avg)}</td>
                    <td>{k.mastery_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
      <div className="between mt">
        <h3 style={{ margin: 0 }}>逐题解析</h3>
        <label className="small"><input type="checkbox" checked={onlyWrong} onChange={(e) => setOnlyWrong(e.target.checked)} /> 只看错题</label>
      </div>
      {list.length === 0 && <div className="card empty mt">全部答对。</div>}
      {list.map((q) => (
        <div className="qcard mt" key={q.id}>
          <QHead q={q} />
          <QBody q={q} />
          <ObjectiveReveal q={q} picked={items[q.id]?.answer ?? null} score={items[q.id]?.score ?? 0} />
        </div>
      ))}
    </>
  )
}
