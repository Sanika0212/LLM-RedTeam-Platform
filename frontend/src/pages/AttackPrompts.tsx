import { useEffect, useState } from 'react'
import { Shield, Zap, FlaskConical } from 'lucide-react'
import { api } from '../services/api'
import type { AttackPrompt } from '../types'

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-900/30 text-red-400 border-red-800',
  high: 'bg-orange-900/30 text-orange-400 border-orange-800',
  medium: 'bg-yellow-900/30 text-yellow-400 border-yellow-800',
  low: 'bg-green-900/30 text-green-400 border-green-800',
}

export default function AttackPrompts() {
  const [prompts, setPrompts] = useState<AttackPrompt[]>([])
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)
  const [seedingResearch, setSeedingResearch] = useState(false)
  const [filter, setFilter] = useState('')

  const load = () => {
    api.getAttackPrompts().then(setPrompts).catch(console.error).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      const result = await api.seedAttackPrompts()
      alert(result.message)
      load()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setSeeding(false)
    }
  }

  const filtered = filter ? prompts.filter(p => p.category === filter) : prompts
  const categories = [...new Set(prompts.map(p => p.category))]

  if (loading) return <div className="p-8 text-gray-500">Loading attack prompts...</div>

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Attack Prompts</h1>
          <p className="text-gray-500 mt-1">Adversarial prompts used for model evaluation</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleSeed} disabled={seeding} className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
            <Zap className="w-4 h-4" /> {seeding ? 'Seeding...' : 'Seed Starter Set'}
          </button>
          <button
            onClick={async () => {
              setSeedingResearch(true)
              try {
                const result = await api.seedResearchDataset()
                alert(`Research dataset imported: ${result.added} prompts added, ${result.skipped_duplicates} duplicates skipped.`)
                load()
              } catch (err: any) { alert(err.message) }
              finally { setSeedingResearch(false) }
            }}
            disabled={seedingResearch}
            className="flex items-center gap-2 px-4 py-2 bg-purple-700 hover:bg-purple-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <FlaskConical className="w-4 h-4" /> {seedingResearch ? 'Importing...' : 'Import Research Dataset'}
          </button>
        </div>
      </div>

      {/* Category Filter */}
      {categories.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => setFilter('')} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${!filter ? 'bg-red-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
            All ({prompts.length})
          </button>
          {categories.map(cat => (
            <button key={cat} onClick={() => setFilter(cat)} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === cat ? 'bg-red-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
              {cat} ({prompts.filter(p => p.category === cat).length})
            </button>
          ))}
        </div>
      )}

      {/* Prompts Grid */}
      {filtered.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <Shield className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-500">No attack prompts yet. Click "Seed Default Prompts" to add the starter set.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(p => (
            <div key={p.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-300">{p.category}</span>
                    {p.subcategory && <span className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-500">{p.subcategory}</span>}
                    <span className={`px-2 py-0.5 rounded text-xs border ${SEVERITY_COLORS[p.severity] || 'bg-gray-800 text-gray-400'}`}>
                      {p.severity}
                    </span>
                  </div>
                  <p className="text-sm text-white leading-relaxed">{p.prompt}</p>
                  {p.description && <p className="text-xs text-gray-500 mt-2">{p.description}</p>}
                </div>
                <span className="text-xs text-gray-600 shrink-0">expects: {p.expected_behavior}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
