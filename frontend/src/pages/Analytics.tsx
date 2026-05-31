import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Legend,
  LineChart, Line, Cell,
} from 'recharts'
import { FlaskConical, TrendingUp, ShieldAlert, Download, RefreshCw } from 'lucide-react'
import { api } from '../services/api'

// ── Types ────────────────────────────────────────────────────────────────────

interface VulnerabilityCategory {
  category: string
  total_prompts: number
  jailbreaks: number
  asr: number
  avg_toxicity: number
  refusal_rate: number
  risk_level: string
}

interface VulnerabilityProfile {
  categories: VulnerabilityCategory[]
  total_prompts: number
  model_id: number | null
}

interface ModelComparisonRow {
  model_id: number
  model_name: string
  provider: string
  total_evaluations: number
  total_prompts_tested: number
  asr: number
  cwss: number
  refusal_rate: number
  avg_toxicity: number
  top_vulnerabilities: { category: string; asr: number }[]
}

interface ModelComparison {
  models: ModelComparisonRow[]
  ranking_metric: string
}

interface TimelineEntry {
  evaluation_id: number
  evaluation_name: string
  model_name: string
  eval_type: string
  completed_at: string | null
  safety_score: number
  jailbreak_rate: number
  robustness_score: number
  hallucination_rate: number
  total_prompts: number
}

interface HeatmapData {
  models: string[]
  categories: string[]
  matrix: Record<string, string | number | null>[]
}

// ── Color utilities ──────────────────────────────────────────────────────────

const RISK_COLORS: Record<string, string> = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#f59e0b',
  Low: '#22c55e',
  None: '#6b7280',
}

const MODEL_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6']

function asrToColor(asr: number | null): string {
  if (asr === null) return '#1f2937'
  if (asr === 0) return '#14532d'
  if (asr < 0.1) return '#166534'
  if (asr < 0.3) return '#ca8a04'
  if (asr < 0.6) return '#c2410c'
  return '#991b1b'
}

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}

// ── Sub-components ───────────────────────────────────────────────────────────

function StatBadge({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-1">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">{children}</h2>
  )
}

// ── Vulnerability Profile Panel ───────────────────────────────────────────────

function VulnerabilityProfilePanel({ data }: { data: VulnerabilityProfile }) {
  if (!data.categories.length) {
    return (
      <p className="text-gray-600 text-center py-12">
        No evaluation results yet. Run evaluations to populate this panel.
      </p>
    )
  }

  const chartData = data.categories.map(c => ({
    category: c.category,
    asr: +(c.asr * 100).toFixed(1),
    refusal_rate: +(c.refusal_rate * 100).toFixed(1),
    toxicity: +(c.avg_toxicity * 100).toFixed(1),
    risk: c.risk_level,
  }))

  return (
    <div className="space-y-6">
      {/* Bar chart */}
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} unit="%" />
          <YAxis type="category" dataKey="category" width={120} tick={{ fill: '#d1d5db', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
            formatter={(v: number, name: string) => [`${v}%`, name]}
          />
          <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
          <Bar dataKey="asr" name="Attack Success Rate" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={RISK_COLORS[entry.risk] || '#6b7280'} />
            ))}
          </Bar>
          <Bar dataKey="refusal_rate" name="Refusal Rate" fill="#3b82f6" radius={[0, 4, 4, 0]} opacity={0.6} />
        </BarChart>
      </ResponsiveContainer>

      {/* Table */}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-800">
            <th className="pb-2 font-medium">Category</th>
            <th className="pb-2 font-medium">Prompts</th>
            <th className="pb-2 font-medium">Jailbreaks</th>
            <th className="pb-2 font-medium">ASR</th>
            <th className="pb-2 font-medium">Refusal Rate</th>
            <th className="pb-2 font-medium">Risk</th>
          </tr>
        </thead>
        <tbody>
          {data.categories.map(c => (
            <tr key={c.category} className="border-b border-gray-800/40 hover:bg-gray-800/20">
              <td className="py-2 text-white font-medium">{c.category}</td>
              <td className="py-2 text-gray-400">{c.total_prompts}</td>
              <td className="py-2 text-gray-400">{c.jailbreaks}</td>
              <td className="py-2 text-white">{fmtPct(c.asr)}</td>
              <td className="py-2 text-blue-400">{fmtPct(c.refusal_rate)}</td>
              <td className="py-2">
                <span
                  className="px-2 py-0.5 rounded text-xs font-medium"
                  style={{ backgroundColor: `${RISK_COLORS[c.risk_level]}22`, color: RISK_COLORS[c.risk_level] }}
                >
                  {c.risk_level}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Model Comparison Panel ───────────────────────────────────────────────────

function ModelComparisonPanel({ data }: { data: ModelComparison }) {
  if (!data.models.length) {
    return (
      <p className="text-gray-600 text-center py-12">
        No models with completed evaluations yet.
      </p>
    )
  }

  const radarData = [
    {
      metric: 'Safety (CWSS)',
      ...Object.fromEntries(data.models.map(m => [m.model_name, +(m.cwss * 100).toFixed(1)])),
    },
    {
      metric: 'Refusal Rate',
      ...Object.fromEntries(data.models.map(m => [m.model_name, +(m.refusal_rate * 100).toFixed(1)])),
    },
    {
      metric: 'Low Toxicity',
      ...Object.fromEntries(data.models.map(m => [m.model_name, +((1 - m.avg_toxicity) * 100).toFixed(1)])),
    },
    {
      metric: 'Jailbreak Resistance',
      ...Object.fromEntries(data.models.map(m => [m.model_name, +((1 - m.asr) * 100).toFixed(1)])),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Rankings */}
      <div className="space-y-2">
        {data.models.map((m, i) => (
          <div key={m.model_id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/30 border border-gray-800">
            <span className="text-2xl font-bold text-gray-600 w-8">#{i + 1}</span>
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{m.model_name}</p>
              <p className="text-gray-500 text-xs">{m.provider} · {m.total_prompts_tested} prompts</p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-green-400 font-bold">{fmtPct(m.cwss)}</p>
              <p className="text-xs text-gray-500">CWSS</p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-red-400 font-bold">{fmtPct(m.asr)}</p>
              <p className="text-xs text-gray-500">ASR</p>
            </div>
          </div>
        ))}
      </div>

      {/* Radar chart (if 2+ models) */}
      {data.models.length >= 2 && (
        <div>
          <p className="text-sm text-gray-500 mb-3">Multi-dimensional safety comparison</p>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <PolarRadiusAxis tick={{ fill: '#6b7280', fontSize: 9 }} domain={[0, 100]} />
              {data.models.slice(0, 4).map((m, i) => (
                <Radar
                  key={m.model_id}
                  name={m.model_name}
                  dataKey={m.model_name}
                  stroke={MODEL_COLORS[i % MODEL_COLORS.length]}
                  fill={MODEL_COLORS[i % MODEL_COLORS.length]}
                  fillOpacity={0.08}
                />
              ))}
              <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// ── Timeline Panel ───────────────────────────────────────────────────────────

function TimelinePanel({ data }: { data: TimelineEntry[] }) {
  if (!data.length) {
    return (
      <p className="text-gray-600 text-center py-12">No completed evaluations over time yet.</p>
    )
  }

  const chartData = data.map((e, i) => ({
    label: `#${e.evaluation_id}`,
    name: e.evaluation_name.length > 18 ? e.evaluation_name.slice(0, 18) + '…' : e.evaluation_name,
    safety: +(e.safety_score * 100).toFixed(1),
    jailbreak: +(e.jailbreak_rate * 100).toFixed(1),
    robustness: +(e.robustness_score * 100).toFixed(1),
    hallucination: +(e.hallucination_rate * 100).toFixed(1),
    model: e.model_name,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="label" tick={{ fill: '#9ca3af', fontSize: 11 }} />
        <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} unit="%" />
        <Tooltip
          contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
          formatter={(v: number, name: string) => [`${v}%`, name]}
          labelFormatter={(label, payload) => payload?.[0]?.payload?.name ?? label}
        />
        <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
        <Line type="monotone" dataKey="safety" stroke="#22c55e" name="Safety Score" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="jailbreak" stroke="#ef4444" name="Jailbreak Rate" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="robustness" stroke="#3b82f6" name="Robustness" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Heatmap Panel ────────────────────────────────────────────────────────────

function HeatmapPanel({ data }: { data: HeatmapData }) {
  if (!data.models.length || !data.categories.length) {
    return (
      <p className="text-gray-600 text-center py-12">
        No cross-model data available. Run evaluations across multiple models and categories.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="text-xs w-full border-collapse">
        <thead>
          <tr>
            <th className="text-left text-gray-500 font-medium p-2 w-36 sticky left-0 bg-gray-900">Model</th>
            {data.categories.map(cat => (
              <th key={cat} className="text-gray-500 font-medium p-2 text-center min-w-[90px]">
                {cat.replace('_', ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.matrix.map((row, i) => (
            <tr key={i} className="hover:bg-gray-800/20">
              <td className="text-white font-medium p-2 sticky left-0 bg-gray-900 truncate max-w-[140px]">
                {String(row.model)}
              </td>
              {data.categories.map(cat => {
                const val = row[cat] as number | null
                const bg = asrToColor(val)
                return (
                  <td
                    key={cat}
                    className="p-2 text-center font-mono"
                    style={{ backgroundColor: bg }}
                    title={val !== null ? `ASR: ${fmtPct(val)}` : 'Not tested'}
                  >
                    {val !== null ? (
                      <span className="text-white">{fmtPct(val)}</span>
                    ) : (
                      <span className="text-gray-700">–</span>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-4 text-xs text-gray-500">
        <span>ASR:</span>
        {[
          { label: '0%', color: '#14532d' },
          { label: '<10%', color: '#166534' },
          { label: '<30%', color: '#ca8a04' },
          { label: '<60%', color: '#c2410c' },
          { label: '≥60%', color: '#991b1b' },
        ].map(({ label, color }) => (
          <div key={label} className="flex items-center gap-1">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: color }} />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Analytics Page ──────────────────────────────────────────────────────

export default function Analytics() {
  const [profile, setProfile] = useState<VulnerabilityProfile | null>(null)
  const [comparison, setComparison] = useState<ModelComparison | null>(null)
  const [timeline, setTimeline] = useState<TimelineEntry[]>([])
  const [heatmap, setHeatmap] = useState<HeatmapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    Promise.all([
      api.getVulnerabilityProfile(),
      api.getModelComparison(),
      api.getEvaluationTimeline(),
      api.getCategoryHeatmap(),
    ])
      .then(([prof, comp, tl, hm]) => {
        setProfile(prof)
        setComparison(comp)
        setTimeline(tl.timeline || [])
        setHeatmap(hm)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Loading analytics...
      </div>
    )
  }

  const topStats = profile && profile.categories.length > 0 ? {
    worstCategory: profile.categories[0],
    totalPrompts: profile.total_prompts,
    avgAsr: profile.categories.reduce((s, c) => s + c.asr, 0) / profile.categories.length,
    criticalCount: profile.categories.filter(c => c.risk_level === 'Critical').length,
  } : null

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FlaskConical className="w-7 h-7 text-purple-400" />
            Research Analytics
          </h1>
          <p className="text-gray-500 mt-1">
            Vulnerability profiles, model comparison, and evaluation trends
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-xl p-4 text-red-400 text-sm">
          Error loading analytics: {error}
        </div>
      )}

      {/* Summary stats */}
      {topStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatBadge
            label="Total Prompts Tested"
            value={topStats.totalPrompts.toLocaleString()}
            color="text-white"
          />
          <StatBadge
            label="Avg Attack Success Rate"
            value={fmtPct(topStats.avgAsr)}
            color={topStats.avgAsr > 0.3 ? 'text-red-400' : topStats.avgAsr > 0.1 ? 'text-yellow-400' : 'text-green-400'}
          />
          <StatBadge
            label="Most Vulnerable Category"
            value={topStats.worstCategory.category}
            color="text-orange-400"
          />
          <StatBadge
            label="Critical Risk Categories"
            value={String(topStats.criticalCount)}
            color={topStats.criticalCount > 0 ? 'text-red-400' : 'text-green-400'}
          />
        </div>
      )}

      {/* Vulnerability Profile */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <SectionTitle>
          <ShieldAlert className="w-5 h-5 text-red-400" />
          Vulnerability Profile by Attack Category
        </SectionTitle>
        {profile ? (
          <VulnerabilityProfilePanel data={profile} />
        ) : (
          <p className="text-gray-600 text-center py-12">No data available</p>
        )}
      </div>

      {/* Model Comparison + Heatmap (side by side) */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <SectionTitle>
            <TrendingUp className="w-5 h-5 text-blue-400" />
            Model Safety Comparison
          </SectionTitle>
          {comparison ? (
            <ModelComparisonPanel data={comparison} />
          ) : (
            <p className="text-gray-600 text-center py-12">No model data</p>
          )}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <SectionTitle>
            <FlaskConical className="w-5 h-5 text-purple-400" />
            Model × Category ASR Heatmap
          </SectionTitle>
          <p className="text-xs text-gray-500 mb-4">
            Attack Success Rate per model per attack category — green = safe, red = vulnerable
          </p>
          {heatmap ? (
            <HeatmapPanel data={heatmap} />
          ) : (
            <p className="text-gray-600 text-center py-12">No cross-model data</p>
          )}
        </div>
      </div>

      {/* Evaluation Timeline */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <SectionTitle>
          <TrendingUp className="w-5 h-5 text-green-400" />
          Evaluation Metrics Timeline
        </SectionTitle>
        <p className="text-xs text-gray-500 mb-4">
          Safety, jailbreak, and robustness scores across all completed evaluations in chronological order
        </p>
        <TimelinePanel data={timeline} />
      </div>

      {/* Research Notes */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Metric Definitions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-500">
          <div>
            <span className="text-gray-300 font-medium">ASR (Attack Success Rate)</span> — Fraction of adversarial prompts
            that elicited non-refusal, compliant responses. ASR = |jailbreaks| / |prompts|.
          </div>
          <div>
            <span className="text-gray-300 font-medium">CWSS (Confidence-Weighted Safety Score)</span> — 1 − ASR, weighted
            by detector confidence. Penalizes high-confidence jailbreaks more than ambiguous cases.
          </div>
          <div>
            <span className="text-gray-300 font-medium">Refusal Rate</span> — Fraction of prompts where a refusal was
            detected. High refusal rate ≠ low ASR if refusals are inconsistent.
          </div>
          <div>
            <span className="text-gray-300 font-medium">Risk Level</span> — None (0%), Low (&lt;10%), Medium (&lt;30%),
            High (&lt;60%), Critical (≥60%) — based on per-category ASR.
          </div>
        </div>
      </div>
    </div>
  )
}
