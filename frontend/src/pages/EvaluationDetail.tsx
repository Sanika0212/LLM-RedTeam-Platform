import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ShieldAlert, ShieldCheck, Download, FileText } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../services/api'
import type { Evaluation, EvaluationResult } from '../types'

export default function EvaluationDetail() {
  const { id } = useParams<{ id: string }>()
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [results, setResults] = useState<EvaluationResult[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    const evalId = Number(id)
    Promise.all([api.getEvaluation(evalId), api.getEvaluationResults(evalId)])
      .then(([e, r]) => { setEvaluation(e); setResults(r) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>
  if (!evaluation) return <div className="p-8 text-red-400">Evaluation not found</div>

  const jailbroken = results.filter(r => r.is_jailbroken)

  const attackTypeData = Object.entries(
    results.reduce<Record<string, { total: number; jailbroken: number }>>((acc, r) => {
      const key = r.attack_type || 'unknown'
      if (!acc[key]) acc[key] = { total: 0, jailbroken: 0 }
      acc[key].total++
      if (r.is_jailbroken) acc[key].jailbroken++
      return acc
    }, {})
  ).map(([type, data]) => ({
    type,
    total: data.total,
    jailbroken: data.jailbroken,
    safe: data.total - data.jailbroken,
    jailbreakRate: +((data.jailbroken / data.total) * 100).toFixed(1),
  }))

  return (
    <div className="p-8 space-y-6">
      <Link to="/evaluations" className="flex items-center gap-2 text-gray-500 hover:text-white transition-colors text-sm">
        <ArrowLeft className="w-4 h-4" /> Back to Evaluations
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{evaluation.name}</h1>
          <p className="text-gray-500 mt-1">{evaluation.description || `${evaluation.eval_type} evaluation`}</p>
        </div>
        <div className="flex items-center gap-3">
          {evaluation.status === 'completed' && id && (
            <>
              <button
                onClick={() => api.exportEvaluationCsv(Number(id)).catch(console.error)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
              >
                <Download className="w-4 h-4" /> Export CSV
              </button>
              <Link
                to={`/analytics`}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-900/30 hover:bg-purple-900/50 text-purple-400 text-sm transition-colors"
              >
                <FileText className="w-4 h-4" /> View Analytics
              </Link>
            </>
          )}
          <span className={`px-3 py-1 rounded text-sm ${
            evaluation.status === 'completed' ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-400'
          }`}>{evaluation.status}</span>
        </div>
      </div>

      {/* Score Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-sm text-gray-500">Safety Score</p>
          <p className="text-2xl font-bold text-green-400">{(evaluation.safety_score * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-sm text-gray-500">Jailbreak Rate</p>
          <p className="text-2xl font-bold text-red-400">{(evaluation.jailbreak_rate * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-sm text-gray-500">Robustness</p>
          <p className="text-2xl font-bold text-blue-400">{(evaluation.robustness_score * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-sm text-gray-500">Total Prompts</p>
          <p className="text-2xl font-bold text-white">{evaluation.total_prompts}</p>
        </div>
      </div>

      {/* Attack Type Breakdown Chart */}
      {attackTypeData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Results by Attack Type</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={attackTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="type" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af' }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
              <Bar dataKey="safe" fill="#22c55e" name="Safe" stackId="a" radius={[0, 0, 0, 0]} />
              <Bar dataKey="jailbroken" fill="#ef4444" name="Jailbroken" stackId="a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Detailed Results */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          Detailed Results ({results.length} prompts, {jailbroken.length} jailbroken)
        </h2>
        <div className="space-y-3 max-h-[600px] overflow-y-auto">
          {results.map(r => (
            <div key={r.id} className={`p-4 rounded-lg border ${r.is_jailbroken ? 'border-red-900/50 bg-red-950/20' : 'border-gray-800 bg-gray-800/30'}`}>
              <div className="flex items-start gap-3">
                {r.is_jailbroken ? (
                  <ShieldAlert className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
                ) : (
                  <ShieldCheck className="w-5 h-5 text-green-400 mt-0.5 shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white">{r.prompt}</p>
                  <div className="flex gap-4 mt-2 text-xs text-gray-500">
                    <span>Type: {r.attack_type}</span>
                    <span>Toxicity: {r.toxicity_score.toFixed(3)}</span>
                    <span>Coherence: {r.coherence_score.toFixed(3)}</span>
                    <span>{r.refusal_detected ? 'Refused' : 'Not refused'}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
