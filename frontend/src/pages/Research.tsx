import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { api } from '../services/api'
import {
  GitBranch, Zap, ArrowRightLeft, Brain, TrendingUp, AlertTriangle, CheckCircle,
} from 'lucide-react'

// ── Transfer Analysis Panel ──────────────────────────────────────────────────

function TransferMatrixPanel() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    api.getTransferAnalysis()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingCard title="Cross-Model Attack Transfer (CATS)" />
  if (error) return <ErrorCard title="Cross-Model Attack Transfer (CATS)" message={error} />

  const matrix = data?.transfer_matrix || {}
  const models = Object.keys(matrix)

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <ArrowRightLeft className="w-5 h-5 text-purple-400" />
        <h2 className="text-lg font-semibold text-white">Cross-Model Attack Transfer (CATS)</h2>
        <span className="ml-auto text-xs text-purple-400 bg-purple-400/10 px-2 py-0.5 rounded-full">
          Novel Metric
        </span>
      </div>
      <p className="text-sm text-gray-400 mb-6">
        CATS(A→B) measures what fraction of attacks that succeeded against Model A also succeeded
        against Model B. High values indicate shared safety vulnerabilities.
      </p>

      {!data?.message && models.length > 0 ? (
        <>
          {/* Transfer Matrix Heatmap */}
          <div className="mb-6">
            <p className="text-xs text-gray-500 mb-3 uppercase tracking-wide">Transfer Matrix (CATS)</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr>
                    <th className="p-2 text-left text-gray-500 text-xs">Source ↓ / Target →</th>
                    {models.map(m => (
                      <th key={m} className="p-2 text-center text-gray-400 text-xs font-medium">{m}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {models.map(source => (
                    <tr key={source} className="border-t border-gray-800">
                      <td className="p-2 text-gray-400 text-xs font-medium">{source}</td>
                      {models.map(target => {
                        const val = matrix[source]?.[target]
                        const isNull = val === null || val === undefined
                        const pct = isNull ? null : Math.round(val * 100)
                        const isDiag = source === target
                        return (
                          <td key={target} className="p-2 text-center">
                            {isDiag ? (
                              <span className="text-gray-600 text-xs">—</span>
                            ) : isNull ? (
                              <span className="text-gray-700 text-xs">N/A</span>
                            ) : (
                              <span
                                className="inline-block px-2 py-0.5 rounded text-xs font-mono font-bold"
                                style={{
                                  backgroundColor: `rgba(239,68,68,${(val ?? 0) * 0.7})`,
                                  color: (val ?? 0) > 0.4 ? '#fff' : '#f87171',
                                }}
                              >
                                {pct}%
                              </span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatMini
              label="Attack Universality Score"
              value={`${((data.attack_universality_score ?? 0) * 100).toFixed(1)}%`}
              sub="Prompts working on ALL models"
            />
            <StatMini
              label="Universal Prompts"
              value={data.n_universal_prompts ?? 0}
              sub="Cross-model jailbreaks"
            />
            <StatMini
              label="Most Transferable"
              value={data.most_transferable_model ?? '—'}
              sub="Highest outgoing CATS"
            />
            <StatMini
              label="Most Resistant"
              value={data.most_resistant_model ?? '—'}
              sub="Lowest incoming CATS"
            />
          </div>
        </>
      ) : (
        <EmptyState
          message={data?.message || 'Run the same prompts on multiple models to populate the transfer matrix.'}
        />
      )}
    </div>
  )
}


// ── Semantic Drift Panel ─────────────────────────────────────────────────────

function SemanticDriftPanel({ evaluationId }: { evaluationId: number | null }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!evaluationId) return
    setLoading(true)
    api.getSemanticDriftAnalysis(evaluationId)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [evaluationId])

  if (!evaluationId) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Brain className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold text-white">Semantic Drift Detector</h2>
          <span className="ml-auto text-xs text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full">Novel</span>
        </div>
        <EmptyState message="Select an evaluation ID in the input above to analyze semantic drift." />
      </div>
    )
  }

  if (loading) return <LoadingCard title="Semantic Drift Detector" />
  if (error) return <ErrorCard title="Semantic Drift Detector" message={error} />

  const analyses = data?.drift_analyses || []
  const summary = data?.summary || {}

  const chartData = analyses.map((a: any) => ({
    category: a.attack_type,
    drift: +(a.drift_score * 100).toFixed(1),
    yesLadder: +(a.yes_ladder_score * 100).toFixed(1),
    creep: +(a.commitment_creep_index * 100).toFixed(1),
  }))

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <Brain className="w-5 h-5 text-blue-400" />
        <h2 className="text-lg font-semibold text-white">Semantic Drift Detector</h2>
        <span className="ml-auto text-xs text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full">Novel</span>
      </div>
      <p className="text-sm text-gray-400 mb-6">
        Detects gradual multi-turn manipulation — the "boiled frog" attack pattern where no single
        turn triggers safety filters, but the cumulative effect is a jailbreak.
      </p>

      {analyses.length > 0 ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <StatMini label="Attack Types Analyzed" value={summary.n_attack_types_analyzed ?? 0} sub="" />
            <StatMini label="Drifting Categories" value={summary.n_drifting ?? 0} sub="Manipulation detected" />
            <StatMini label="Max Drift Score" value={`${((summary.max_drift_score ?? 0) * 100).toFixed(1)}%`} sub="" />
            <StatMini label="Highest Drift" value={summary.highest_drift_category ?? '—'} sub="Category" />
          </div>

          {chartData.length > 0 && (
            <div className="mb-6">
              <p className="text-xs text-gray-500 mb-3 uppercase tracking-wide">Drift Metrics by Attack Category</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} margin={{ top: 0, right: 20, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="category" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <YAxis unit="%" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                    labelStyle={{ color: '#f9fafb' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="drift" name="Drift Score" fill="#3b82f6" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="yesLadder" name="Yes-Ladder" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="creep" name="Commitment Creep" fill="#06b6d4" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Detailed table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="pb-2 text-left text-gray-500 text-xs uppercase">Category</th>
                  <th className="pb-2 text-center text-gray-500 text-xs uppercase">Drifting?</th>
                  <th className="pb-2 text-center text-gray-500 text-xs uppercase">Drift</th>
                  <th className="pb-2 text-center text-gray-500 text-xs uppercase">Velocity</th>
                  <th className="pb-2 text-center text-gray-500 text-xs uppercase">Yes-Ladder</th>
                  <th className="pb-2 text-center text-gray-500 text-xs uppercase">Onset Turn</th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((a: any) => (
                  <tr key={a.attack_type} className="border-t border-gray-800/50">
                    <td className="py-2 text-gray-300">{a.attack_type}</td>
                    <td className="py-2 text-center">
                      {a.is_drifting
                        ? <span className="text-red-400 flex items-center justify-center gap-1"><AlertTriangle className="w-3 h-3" /> Yes</span>
                        : <span className="text-green-400 flex items-center justify-center gap-1"><CheckCircle className="w-3 h-3" /> No</span>}
                    </td>
                    <td className="py-2 text-center text-white font-mono">{(a.drift_score * 100).toFixed(1)}%</td>
                    <td className="py-2 text-center text-gray-400 font-mono">{(a.drift_velocity * 100).toFixed(1)}%</td>
                    <td className="py-2 text-center text-purple-400 font-mono">{(a.yes_ladder_score * 100).toFixed(1)}%</td>
                    <td className="py-2 text-center text-gray-400">{a.manipulation_onset_turn ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <EmptyState message={data?.message || 'No multi-turn conversation data found for this evaluation.'} />
      )}
    </div>
  )
}


// ── Adaptive Budget Panel ────────────────────────────────────────────────────

function AdaptiveBudgetPanel() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [budget, setBudget] = useState(100)

  const run = () => {
    setLoading(true)
    setError(null)
    api.getAdaptiveBudgetSimulation(budget)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  const asrData = data ? Object.entries(data.observed_category_asrs || {}).map(([cat, asr]) => ({
    category: cat,
    asr: +((asr as number) * 100).toFixed(1),
  })) : []

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <TrendingUp className="w-5 h-5 text-green-400" />
        <h2 className="text-lg font-semibold text-white">Adaptive Budget Allocation (Thompson Sampling)</h2>
        <span className="ml-auto text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded-full">Novel</span>
      </div>
      <p className="text-sm text-gray-400 mb-6">
        Bayesian Adaptive Budget Allocation dynamically focuses evaluation queries on the most
        vulnerable attack categories using Thompson Sampling, improving jailbreak discovery
        efficiency vs. uniform allocation.
      </p>

      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Query Budget:</label>
          <input
            type="number"
            value={budget}
            onChange={e => setBudget(Number(e.target.value))}
            min={20}
            max={500}
            className="w-24 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
          />
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="px-4 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? 'Simulating…' : 'Run Simulation'}
        </button>
      </div>

      {error && <ErrorCard title="" message={error} />}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <StatMini
              label="Adaptive ASR"
              value={`${(data.simulation?.mean_adaptive_asr * 100).toFixed(1)}%`}
              sub="Thompson Sampling"
              highlight
            />
            <StatMini
              label="Uniform ASR"
              value={`${(data.simulation?.mean_uniform_asr * 100).toFixed(1)}%`}
              sub="Baseline strategy"
            />
            <StatMini
              label="Efficiency Gain"
              value={`+${(data.interpretation?.efficiency_gain_pct ?? 0).toFixed(1)}%`}
              sub="More jailbreaks found"
              highlight
            />
            <StatMini
              label="Simulations"
              value={data.simulation?.n_simulations ?? 0}
              sub="Monte Carlo runs"
            />
          </div>

          {data.interpretation?.recommendation && (
            <div className="mb-6 px-4 py-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <p className="text-sm text-green-300">{data.interpretation.recommendation}</p>
            </div>
          )}

          {asrData.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-3 uppercase tracking-wide">
                Observed ASR per Category (used for simulation)
              </p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={asrData} margin={{ top: 0, right: 20, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="category" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <YAxis unit="%" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                    labelStyle={{ color: '#f9fafb' }}
                  />
                  <Bar dataKey="asr" name="ASR %" fill="#22c55e" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {!data && !loading && (
        <EmptyState message="Click 'Run Simulation' to compare Thompson Sampling vs. uniform budget allocation." />
      )}
    </div>
  )
}


// ── PAIR Failure Mode Panel ──────────────────────────────────────────────────

function PairFailureModePanel({ evaluationId }: { evaluationId: number | null }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!evaluationId) return
    setLoading(true)
    api.getPairFailureModes(evaluationId)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [evaluationId])

  if (!evaluationId) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Zap className="w-5 h-5 text-yellow-400" />
          <h2 className="text-lg font-semibold text-white">PAIR Failure Mode Analysis</h2>
          <span className="ml-auto text-xs text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded-full">Novel</span>
        </div>
        <EmptyState message="Select an evaluation ID above to analyze failure modes." />
      </div>
    )
  }

  if (loading) return <LoadingCard title="PAIR Failure Mode Analysis" />
  if (error) return <ErrorCard title="PAIR Failure Mode Analysis" message={error} />

  const dist = data?.failure_mode_distribution || {}
  const chartData = Object.entries(dist).map(([mode, pct]) => ({
    mode: mode.replace('_', ' '),
    pct: +((pct as number) * 100).toFixed(1),
  })).sort((a, b) => b.pct - a.pct)

  const modeDescriptions: Record<string, string> = {
    explicit_refusal: "Direct refusal (I can't / I won't)",
    polite_deflection: 'Offers alternative without refusing directly',
    topic_shift: 'Answers a safer interpretation of the question',
    too_vague: 'Abstract response with no actionable detail',
    too_explicit: 'Safety filter triggered by direct phrasing',
    overcorrection: 'Long moral lecture, excessive disclaimers',
    truncated: 'Empty or very short response',
    unknown: 'No clear failure pattern',
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <Zap className="w-5 h-5 text-yellow-400" />
        <h2 className="text-lg font-semibold text-white">PAIR Failure Mode Analysis</h2>
        <span className="ml-auto text-xs text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded-full">Novel</span>
      </div>
      <p className="text-sm text-gray-400 mb-6">
        PAIR's failure mode taxonomy classifies <em>why</em> each jailbreak attempt failed —
        enabling targeted refinement rather than random mutation. This is the first systematic
        failure mode classification in LLM red-teaming.
      </p>

      {data?.n_failed_prompts > 0 ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
            <StatMini label="Failed Prompts" value={data.n_failed_prompts} sub="Analyzed" />
            <StatMini label="Dominant Mode" value={data.dominant_failure_mode?.replace('_', ' ') ?? '—'} sub="Most common failure" />
            <StatMini label="Refinement Strategy" value="" sub={data.dominant_refinement_strategy ?? '—'} />
          </div>

          {chartData.length > 0 && (
            <div className="mb-6">
              <p className="text-xs text-gray-500 mb-3 uppercase tracking-wide">Failure Mode Distribution</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 40, left: 80, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis type="number" unit="%" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <YAxis dataKey="mode" type="category" tick={{ fill: '#9ca3af', fontSize: 11 }} width={75} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                    labelStyle={{ color: '#f9fafb' }}
                  />
                  <Bar dataKey="pct" name="% of Failures" fill="#f59e0b" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Mode descriptions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {Object.entries(data.mode_counts || {})
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .map(([mode, count]) => (
                <div key={mode} className="px-3 py-2 bg-gray-800/50 rounded-lg">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs text-white font-medium">{mode.replace(/_/g, ' ')}</span>
                    <span className="text-xs text-yellow-400 font-mono">{count as number}×</span>
                  </div>
                  <p className="text-xs text-gray-500">{modeDescriptions[mode] ?? mode}</p>
                </div>
              ))}
          </div>
        </>
      ) : (
        <EmptyState message={data?.message || 'No failed prompt data found for this evaluation.'} />
      )}
    </div>
  )
}


// ── Shared Sub-Components ────────────────────────────────────────────────────

function StatMini({ label, value, sub, highlight = false }: {
  label: string; value: any; sub: string; highlight?: boolean
}) {
  return (
    <div className={`px-4 py-3 rounded-lg border ${highlight ? 'border-green-500/30 bg-green-500/5' : 'border-gray-800 bg-gray-800/50'}`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-lg font-bold ${highlight ? 'text-green-400' : 'text-white'}`}>{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  )
}

function LoadingCard({ title }: { title: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">{title}</h2>
      <div className="flex items-center gap-2 text-gray-500">
        <div className="w-4 h-4 border-2 border-gray-500 border-t-white rounded-full animate-spin" />
        <span className="text-sm">Loading…</span>
      </div>
    </div>
  )
}

function ErrorCard({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      {title && <h2 className="text-lg font-semibold text-white mb-4">{title}</h2>}
      <p className="text-sm text-red-400">{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <GitBranch className="w-10 h-10 text-gray-700 mb-3" />
      <p className="text-sm text-gray-500 max-w-sm">{message}</p>
    </div>
  )
}


// ── Strategy Reference Card ──────────────────────────────────────────────────

function StrategyReferenceCard() {
  const strategies = [
    {
      name: 'Crescendo',
      ref: 'Russinovich et al., 2024',
      description: 'Multi-turn escalation from benign opener to harmful target. Exploits recency bias.',
      novelty: 'Now analyzed with Semantic Drift Detector.',
      icon: '↗',
      color: 'orange',
    },
    {
      name: 'TAP',
      ref: 'Mehrotra et al., 2023 · arXiv:2312.02119',
      description: 'Tree of Attacks with Pruning. Beam search over prompt mutations with scoring.',
      novelty: 'Mutation chains tracked via Genealogy Analyzer.',
      icon: '🌳',
      color: 'blue',
    },
    {
      name: 'PAIR',
      ref: 'Chao et al., 2023 · arXiv:2310.08419',
      description: 'Iterative refinement of failed prompts toward the target intent.',
      novelty: 'Extended with Failure Mode Taxonomy — 7 classified failure types.',
      icon: '🔄',
      color: 'yellow',
    },
  ]

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Attack Strategies</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {strategies.map(s => (
          <div key={s.name} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
            <div className="text-2xl mb-2">{s.icon}</div>
            <h3 className="text-white font-semibold mb-0.5">{s.name}</h3>
            <p className="text-xs text-gray-500 mb-2">{s.ref}</p>
            <p className="text-sm text-gray-400 mb-3">{s.description}</p>
            <p className="text-xs text-purple-400 border-t border-gray-700 pt-2">
              ✦ {s.novelty}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}


// ── Main Research Page ───────────────────────────────────────────────────────

export default function Research() {
  const [evalId, setEvalId] = useState<string>('')
  const parsedEvalId = evalId ? parseInt(evalId, 10) : null

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Research Analytics</h1>
        <p className="text-gray-400 mt-1 text-sm">
          Novel research metrics beyond standard red-team evaluation:
          cross-model attack transfer, semantic drift detection, adaptive budget allocation,
          and PAIR failure mode taxonomy.
        </p>
      </div>

      {/* Evaluation ID input for per-evaluation analyses */}
      <div className="flex items-center gap-4 px-4 py-3 bg-gray-900 border border-gray-800 rounded-xl">
        <span className="text-sm text-gray-400">Evaluation ID for per-evaluation analyses:</span>
        <input
          type="number"
          value={evalId}
          onChange={e => setEvalId(e.target.value)}
          placeholder="e.g. 1"
          className="w-28 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
        />
        <span className="text-xs text-gray-600">Used for Semantic Drift and PAIR failure mode panels below.</span>
      </div>

      {/* Strategy Reference */}
      <StrategyReferenceCard />

      {/* Novel Analytics: Transfer Matrix */}
      <TransferMatrixPanel />

      {/* Novel Analytics: Adaptive Budget */}
      <AdaptiveBudgetPanel />

      {/* Grid: Semantic Drift + PAIR Failure Modes */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <SemanticDriftPanel evaluationId={parsedEvalId} />
        <PairFailureModePanel evaluationId={parsedEvalId} />
      </div>

      {/* Novelty Summary */}
      <div className="bg-gray-900 border border-purple-500/20 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Novel Research Contributions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          {[
            {
              title: 'CATS — Cross-Model Attack Transfer Score',
              desc: 'First framework metric quantifying attack transferability between models. Reveals shared safety vulnerabilities across the model ecosystem.',
            },
            {
              title: 'AUS — Attack Universality Score',
              desc: 'Identifies prompts that jailbreak ALL tested models simultaneously — the most dangerous category of adversarial inputs.',
            },
            {
              title: 'Semantic Drift Detector',
              desc: 'First multi-turn manipulation detector using yes-ladder scoring, commitment creep index, and drift velocity to catch gradual attacks.',
            },
            {
              title: 'PAIR Failure Mode Taxonomy',
              desc: '7-class failure mode classifier that enables targeted refinement. The first systematic taxonomy of LLM refusal mechanisms in adversarial contexts.',
            },
            {
              title: 'Bayesian Adaptive Budget Allocation (BABA)',
              desc: 'First application of Thompson Sampling to red-team query budget allocation, demonstrating improved jailbreak discovery per query budget.',
            },
            {
              title: 'Attack Genealogy Tracker',
              desc: 'Tracks the full mutation lineage from seed prompts to jailbreaks, computing mutation efficiency and seed productivity metrics.',
            },
          ].map(item => (
            <div key={item.title} className="flex gap-3">
              <span className="text-purple-400 mt-0.5">✦</span>
              <div>
                <p className="text-white font-medium">{item.title}</p>
                <p className="text-gray-500 text-xs mt-0.5">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
