export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, '无法连接到本地服务，请确认 Docker 容器（或 start.bat 窗口）仍在运行')
  }
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    const detail = data?.detail
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join('；') : `请求失败（${res.status}）`
    throw new ApiError(res.status, msg)
  }
  return data as T
}

export const api = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body?: unknown) => request<T>('POST', url, body ?? {}),
  put: <T>(url: string, body?: unknown) => request<T>('PUT', url, body ?? {}),
}

export type Level = 'P0' | 'P1' | 'P2'
export type QType = 'single' | 'multi' | 'judge' | 'case' | 'short' | 'scenario' | 'design' | 'oral'
export const OBJECTIVE: QType[] = ['single', 'multi', 'judge', 'case']

export interface KeyPoint {
  text: string
  dim: 'concept' | 'principle' | 'project' | 'engineering'
}

export interface Question {
  id: string
  kp: string | null
  type: QType
  question: string
  code: string | null
  lang: string
  options: string[] | null
  answer: number[] | boolean | null
  explain: string | null
  key_points: KeyPoint[] | null
  reference: string | null
  difficulty: number | null
  oral: string | null
  category: string
  kp_name: string | null
  kp_level: Level | null
  day: number | null
  source: string | null
}

export type ObjAnswer = number[] | boolean

export interface Attempt {
  id: number
  question_id: string
  answer: string
  checks: number[] | null
  expression: number | null
  score: number
  dims: Record<string, number> | null
  gave_up: boolean
  context: string
  created_at: string
}

export interface AttemptResult {
  attempt_id: number
  score: number
  dims: Record<string, number> | null
  wrong: boolean
  level: number | null
  level_name: string | null
  correct?: boolean
  answer?: number[] | boolean
  explain?: string
}

export interface KpResult {
  id: string
  name: string
  level: Level
  day: number
  avg: number
  mastery: number
  mastery_name: string
}

export interface QuizSession {
  id: number
  kind: 'review' | 'test' | 'exam'
  ref: number
  created_at: string
  submitted: boolean
  answers: Record<string, ObjAnswer>
  score: number | null
  passed: boolean | null
  result: {
    items?: Record<string, { score: number; answer: ObjAnswer | null; correct: boolean; points: number; got: number }>
    kps?: KpResult[]
    weak?: KpResult[]
    by_type?: Record<string, { got: number; total: number }>
  } | null
  pass_score: number
  points: Record<string, number> | null
  questions: Question[]
  reasons?: Record<string, string>
  title?: string
}

export interface Resource {
  title: string
  url: string
  kind: 'video' | 'article' | 'doc' | 'course' | 'repo'
  lang: 'zh' | 'en'
  minutes: number | null
  note: string
}

export interface KnowledgePoint {
  id: string
  name: string
  level: Level
  summary: string
  analogy: string | null
  why: string
  problem: string
  principle: string
  scenarios: string
  code: string | null
  pitfalls: string
  interview_asks: (string | { question: string; answer: string })[]
  project_example: string
  freshness: string | null
  sources: { title: string; url: string }[]
  mastery: number
  mastery_name: string
  note: string
  outdated: boolean
}

export type Stage = 'review' | 'lesson' | 'test' | 'interview' | 'summary'

export interface ReviewState {
  needed: boolean
  done: boolean
  size: number
  gap: number
  pending_id: number | null
}

export interface DayState {
  day: number
  started: boolean
  completed: boolean
  completed_at: string | null
  best_score: number | null
  tests_taken: number
  pending_test: number | null
  stage: Stage
  done: Record<Stage, boolean>
  learned: string[]
  interview_done: number
  interview_total: number
  review: ReviewState
  seconds: Record<string, number>
}

export interface DailyReport {
  day: number
  title: string
  test_score: number
  tests_taken: number
  kps: { id: string; name: string; level: Level; mastery: number; mastery_name: string; test_avg: number | null; next_review: string | null }[]
  weak: string[]
  wrong: { question_id: string; text: string; score: number }[]
  interview_done: number
  interview_total: number
  minutes: number
  tomorrow: { day: number; title: string; goals: string[] } | null
  exam_next: boolean
  projects: { id: string; name: string; minutes: number }[]
}

export interface DayDetail {
  day: number
  phase: number
  phase_title: string
  title: string
  goals: string[]
  minutes: number
  resources: Resource[]
  sources: { title: string; url: string }[]
  knowledge_points: KnowledgePoint[]
  test_pool: number
  interview: Question[]
  interview_attempts: Record<string, Attempt>
  projects: { id: string; name: string; minutes: number; project: string }[]
  available: boolean
  why: string
  state: DayState
  report: DailyReport | null
}

export const DIM_NAMES: Record<string, string> = {
  concept: '概念',
  principle: '原理',
  project: '结合项目',
  engineering: '工程思维',
  expression: '表达',
}

export const TYPE_NAMES: Record<string, string> = {
  single: '单选题',
  multi: '多选题',
  judge: '判断题',
  case: '案例分析',
  short: '简答题',
  scenario: '场景题',
  design: '设计题',
  oral: '口述题',
}

export const CATEGORY_NAMES: Record<string, string> = {
  python_backend: 'Python 与后端',
  llm: '大模型应用',
  rag: 'RAG',
  agent: 'Agent',
  eval: '评测与可观测',
  engineering: '生产工程与安全',
  architecture: '架构与求职',
}

export const RESOURCE_KIND: Record<string, string> = {
  video: '视频',
  article: '文章',
  doc: '文档',
  course: '课程',
  repo: '代码',
}

export const MASTERY_NAMES = ['未学习', '已学习', '初步理解', '基本掌握', '熟练掌握']

export function fmtScore(v: number | null | undefined): string {
  return v === null || v === undefined ? '—' : String(Math.round(v))
}

export const pad = (n: number) => String(n).padStart(2, '0')
