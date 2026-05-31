import { useState } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { Shield, BarChart3, Swords, Trophy, Database, LogOut, FlaskConical, Microscope } from 'lucide-react'
import { isAuthenticated, clearToken } from './services/api'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Evaluations from './pages/Evaluations'
import EvaluationDetail from './pages/EvaluationDetail'
import Models from './pages/Models'
import Leaderboard from './pages/Leaderboard'
import AttackPrompts from './pages/AttackPrompts'
import Analytics from './pages/Analytics'
import Research from './pages/Research'

const navItems = [
  { to: '/', label: 'Dashboard', icon: BarChart3 },
  { to: '/evaluations', label: 'Evaluations', icon: Swords },
  { to: '/models', label: 'Models', icon: Database },
  { to: '/leaderboard', label: 'Leaderboard', icon: Trophy },
  { to: '/attack-prompts', label: 'Attack Prompts', icon: Shield },
  { to: '/analytics', label: 'Analytics', icon: FlaskConical },
  { to: '/research', label: 'Research', icon: Microscope },
]

export default function App() {
  const location = useLocation()
  const [authed, setAuthed] = useState(isAuthenticated())

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />
  }

  const handleLogout = () => {
    clearToken()
    setAuthed(false)
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-red-500" />
            <div>
              <h1 className="text-lg font-bold text-white">LLM Red-Team</h1>
              <p className="text-xs text-gray-500">Evaluation Platform</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => {
            const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            )
          })}
        </nav>
        <div className="p-4 border-t border-gray-800 space-y-2">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 w-full rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
          <p className="text-xs text-gray-600">v1.0.0 Research</p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/evaluations" element={<Evaluations />} />
          <Route path="/evaluations/:id" element={<EvaluationDetail />} />
          <Route path="/models" element={<Models />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/attack-prompts" element={<AttackPrompts />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/research" element={<Research />} />
        </Routes>
      </main>
    </div>
  )
}
