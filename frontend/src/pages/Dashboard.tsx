import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Shield, Swords, Database, AlertTriangle } from 'lucide-react'
import { api } from '../services/api'
import type { Stats, Evaluation } from '../types'

const COLORS = ['#ef4444', '#f59e0b', '#22c55e', '#3b82f6']

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.getStats(), api.getEvaluations()])
      .then(([s, e]) => { setStats(s); setEvaluations(e) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-gray-500">Loading dashboard...</div>

  const statCards = stats ? [
    { label: 'Total Models', value: stats.total_models, icon: Database, color: 'text-blue-400' },
    { label: 'Evaluations', value: stats.total_evaluations, icon: Swords, color: 'text-purple-400' },
    { label: 'Avg Safety Score', value: `${(stats.average_safety_score * 100).toFixed(1)}%`, icon: Shield, color: 'text-green-400' },
    { label: 'Avg Jailbreak Rate', value: `${(stats.average_jailbreak_rate * 100).toFixed(1)}%`, icon: AlertTriangle, color: 'text-red-400' },
  ] : []

  const evalChartData = evaluations
    .filter(e => e.status === 'completed')
    .slice(0, 10)
    .map(e => ({
      name: e.name.length > 15 ? e.name.slice(0, 15) + '...' : e.name,
      safety: +(e.safety_score * 100).toFixed(1),
      jailbreak: +(e.jailbreak_rate * 100).toFixed(1),
      robustness: +(e.robustness_score * 100).toFixed(1),
    }))

  const statusData = [
    { name: 'Completed', value: evaluations.filter(e => e.status === 'completed').length },
    { name: 'Running', value: evaluations.filter(e => e.status === 'running').length },
    { name: 'Pending', value: evaluations.filter(e => e.status === 'pending').length },
    { name: 'Failed', value: evaluations.filter(e => e.status === 'failed').length },
  ].filter(d => d.value > 0)

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of LLM security evaluations</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{label}</p>
                <p className="text-2xl font-bold text-white mt-1">{value}</p>
              </div>
              <Icon className={`w-8 h-8 ${color} opacity-60`} />
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Evaluation Scores */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Evaluation Scores</h2>
          {evalChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={evalChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <YAxis tick={{ fill: '#9ca3af' }} domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                <Bar dataKey="safety" fill="#22c55e" name="Safety %" radius={[4, 4, 0, 0]} />
                <Bar dataKey="jailbreak" fill="#ef4444" name="Jailbreak %" radius={[4, 4, 0, 0]} />
                <Bar dataKey="robustness" fill="#3b82f6" name="Robustness %" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-600 text-center py-16">No completed evaluations yet. Run an evaluation to see data here.</p>
          )}
        </div>

        {/* Status Breakdown */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Evaluation Status</h2>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={statusData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={4} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-600 text-center py-16">No evaluations yet</p>
          )}
        </div>
      </div>

      {/* Recent Evaluations */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Recent Evaluations</h2>
        {evaluations.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 text-left text-sm text-gray-500">
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Safety</th>
                <th className="pb-3 font-medium">Jailbreak Rate</th>
              </tr>
            </thead>
            <tbody>
              {evaluations.slice(0, 5).map(e => (
                <tr key={e.id} className="border-b border-gray-800/50">
                  <td className="py-3 text-white">{e.name}</td>
                  <td className="py-3"><span className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-300">{e.eval_type}</span></td>
                  <td className="py-3">
                    <span className={`px-2 py-1 rounded text-xs ${
                      e.status === 'completed' ? 'bg-green-900/30 text-green-400' :
                      e.status === 'running' ? 'bg-blue-900/30 text-blue-400' :
                      e.status === 'failed' ? 'bg-red-900/30 text-red-400' :
                      'bg-gray-800 text-gray-400'
                    }`}>{e.status}</span>
                  </td>
                  <td className="py-3 text-white">{(e.safety_score * 100).toFixed(1)}%</td>
                  <td className="py-3 text-red-400">{(e.jailbreak_rate * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-600 text-center py-8">No evaluations yet. Create one to get started.</p>
        )}
      </div>
    </div>
  )
}
