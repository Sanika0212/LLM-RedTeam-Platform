import { useEffect, useState } from 'react'
import { Trophy, Medal } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts'
import { api } from '../services/api'
import type { LLMModel } from '../types'

export default function Leaderboard() {
  const [models, setModels] = useState<LLMModel[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getModels()
      .then(m => setModels(m.filter((m: LLMModel) => m.total_evaluations > 0).sort((a: LLMModel, b: LLMModel) => b.safety_score - a.safety_score)))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-gray-500">Loading leaderboard...</div>

  const chartData = models.map(m => ({
    name: m.name.length > 12 ? m.name.slice(0, 12) + '...' : m.name,
    safety: +(m.safety_score * 100).toFixed(1),
    robustness: +(m.robustness_score * 100).toFixed(1),
  }))

  const radarData = models.length > 0 ? [
    { metric: 'Safety', ...Object.fromEntries(models.map(m => [m.name, +(m.safety_score * 100).toFixed(1)])) },
    { metric: 'Robustness', ...Object.fromEntries(models.map(m => [m.name, +(m.robustness_score * 100).toFixed(1)])) },
    { metric: 'Evaluations', ...Object.fromEntries(models.map(m => [m.name, Math.min(m.total_evaluations * 10, 100)])) },
  ] : []

  const MEDAL_COLORS = ['text-yellow-400', 'text-gray-400', 'text-amber-600']

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Trophy className="w-7 h-7 text-yellow-400" /> Leaderboard
        </h1>
        <p className="text-gray-500 mt-1">Model rankings by safety and robustness scores</p>
      </div>

      {models.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <Trophy className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-500">No evaluated models yet. Run evaluations to populate the leaderboard.</p>
        </div>
      ) : (
        <>
          {/* Rankings Table */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800 text-left text-sm text-gray-500">
                  <th className="px-6 py-3 font-medium w-16">Rank</th>
                  <th className="px-6 py-3 font-medium">Model</th>
                  <th className="px-6 py-3 font-medium">Provider</th>
                  <th className="px-6 py-3 font-medium">Safety Score</th>
                  <th className="px-6 py-3 font-medium">Robustness</th>
                  <th className="px-6 py-3 font-medium">Evaluations</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m, i) => (
                  <tr key={m.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-6 py-4">
                      {i < 3 ? (
                        <Medal className={`w-5 h-5 ${MEDAL_COLORS[i]}`} />
                      ) : (
                        <span className="text-gray-500 text-sm">{i + 1}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-white font-medium">{m.name}</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-300">{m.provider}</span></td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div className="h-full bg-green-500 rounded-full" style={{ width: `${m.safety_score * 100}%` }} />
                        </div>
                        <span className="text-green-400 text-sm">{(m.safety_score * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${m.robustness_score * 100}%` }} />
                        </div>
                        <span className="text-blue-400 text-sm">{(m.robustness_score * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-400">{m.total_evaluations}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Comparison Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Score Comparison</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#9ca3af' }} domain={[0, 100]} />
                  <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                  <Bar dataKey="safety" fill="#22c55e" name="Safety %" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="robustness" fill="#3b82f6" name="Robustness %" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {models.length >= 2 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Radar Comparison</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#374151" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                    <PolarRadiusAxis tick={{ fill: '#6b7280' }} domain={[0, 100]} />
                    {models.slice(0, 3).map((m, i) => (
                      <Radar key={m.id} name={m.name} dataKey={m.name} stroke={['#22c55e', '#3b82f6', '#f59e0b'][i]} fill={['#22c55e', '#3b82f6', '#f59e0b'][i]} fillOpacity={0.1} />
                    ))}
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
