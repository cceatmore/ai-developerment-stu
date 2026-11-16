import { useEffect, useState } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './api'
import Dashboard from './pages/Dashboard'
import Daily from './pages/Daily'
import Exams from './pages/Exams'
import Mock from './pages/Mock'
import Projects from './pages/Projects'
import Reports from './pages/Reports'
import Review from './pages/Review'
import Settings from './pages/Settings'

interface Counts {
  current_day: number
  review: { needed: boolean; size: number }
  wrong_open: number
}

export default function App() {
  const loc = useLocation()
  const [counts, setCounts] = useState<Counts | null>(null)

  useEffect(() => {
    api.get<Counts>('/api/dashboard').then(setCounts).catch(() => setCounts(null))
  }, [loc.pathname])

  const links: [string, string, number?][] = [
    ['/', '驾驶舱'],
    [`/day/${counts?.current_day ?? 1}`, '今日学习', counts?.review.needed ? counts.review.size : undefined],
    ['/review', '复习与错题', counts?.wrong_open],
    ['/exams', '阶段卷'],
    ['/projects', '实践项目'],
    ['/mock', '模拟面试'],
    ['/reports', '学习报告'],
    ['/settings', '数据与设置'],
  ]
  const nav = links.map(([to, name, badge]) => (
    <NavLink
      key={name}
      to={to}
      end={to === '/'}
      className={({ isActive }) => (isActive || (name === '今日学习' && loc.pathname.startsWith('/day/')) || (name === '实践项目' && loc.pathname.startsWith('/projects')) ? 'active' : '')}
    >
      {name}
      {badge ? <span className="badge">{badge}</span> : null}
    </NavLink>
  ))

  return (
    <div className="layout">
      <aside className="side">
        <div className="brand">
          AI 应用 + Agent 工程师
          <small>50 个学习日 · 每天 ≥1 小时</small>
        </div>
        {nav}
      </aside>
      <nav className="topnav">{nav}</nav>
      <main className="main">
        <div className="container">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/day/:day" element={<Daily />} />
            <Route path="/review" element={<Review />} />
            <Route path="/exams" element={<Exams />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/projects/:pid" element={<Projects />} />
            <Route path="/projects/:pid/:tab" element={<Projects />} />
            <Route path="/mock" element={<Mock />} />
            <Route path="/mock/:id" element={<Mock />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<div className="empty">页面不存在</div>} />
          </Routes>
        </div>
      </main>
    </div>
  )
}
