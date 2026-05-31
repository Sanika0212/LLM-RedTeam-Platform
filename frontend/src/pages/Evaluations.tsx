import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Play, Trash2, ExternalLink } from 'lucide-react'
import { api } from '../services/api'
import type { Evaluation, LLMModel } from '../types'

const EVAL_TYPES = ['safety', 'robustness', 'jailbreak', 'accuracy']

export default function Evaluations() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [models, setModels] = useState<LLMModel[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', model_id: 0, eval_type: 'safety' })
  const [error, setError] = useState('')
  const [running, setRunning] = useState<number | null>(null)

  const load = () => {
    api.getEvaluations().then(setEvaluations).catch(console.error)
    api.getModels().then(setModels).catch(console.error)
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.model_id) { setError('Select a model'); return }
    try {
      await api.createEvaluation(form)
      setForm({ name: '', description: '', model_id: 0, eval_type: 'safety' })
      setShowForm(false)
      load()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleRun = async (id: number) => {
    setRunning(id)
    try {
      await api.runEvaluation(id)
      load()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setRunning(null)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this evaluation and all its results?')) return
    await api.deleteEvaluation(id)
    load()
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Evaluations</h1>
          <p className="text-gray-500 mt-1">Run adversarial evaluations against models</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors">
          <Plus className="w-4 h-4" /> New Evaluation
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name</label>
              <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} required className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-red-500" placeholder="Safety Eval - GPT-4" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Model</label>
              <select value={form.model_id} onChange={e => setForm({...form, model_id: Number(e.target.value)})} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-red-500">
                <option value={0}>Select a model...</option>
                {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Type</label>
              <select value={form.eval_type} onChange={e => setForm({...form, eval_type: e.target.value})} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-red-500">
                {EVAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Description</label>
              <input value={form.description} onChange={e => setForm({...form, description: e.target.value})} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-red-500" placeholder="Optional description" />
            </div>
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium">Create</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm">Cancel</button>
          </div>
        </form>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800 text-left text-sm text-gray-500">
              <th className="px-6 py-3 font-medium">Name</th>
              <th className="px-6 py-3 font-medium">Type</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Prompts</th>
              <th className="px-6 py-3 font-medium">Safety</th>
              <th className="px-6 py-3 font-medium">Jailbreak</th>
              <th className="px-6 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {evaluations.map(e => (
              <tr key={e.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-6 py-4 text-white font-medium">{e.name}</td>
                <td className="px-6 py-4"><span className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-300">{e.eval_type}</span></td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs ${
                    e.status === 'completed' ? 'bg-green-900/30 text-green-400' :
                    e.status === 'running' ? 'bg-blue-900/30 text-blue-400' :
                    e.status === 'failed' ? 'bg-red-900/30 text-red-400' :
                    'bg-yellow-900/30 text-yellow-400'
                  }`}>{e.status}</span>
                </td>
                <td className="px-6 py-4 text-gray-400">{e.completed_prompts}/{e.total_prompts}</td>
                <td className="px-6 py-4 text-green-400">{(e.safety_score * 100).toFixed(1)}%</td>
                <td className="px-6 py-4 text-red-400">{(e.jailbreak_rate * 100).toFixed(1)}%</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    {e.status === 'pending' && (
                      <button onClick={() => handleRun(e.id)} disabled={running === e.id} className="p-1.5 text-green-400 hover:bg-green-900/30 rounded transition-colors disabled:opacity-50" title="Run">
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    {e.status === 'completed' && (
                      <Link to={`/evaluations/${e.id}`} className="p-1.5 text-blue-400 hover:bg-blue-900/30 rounded transition-colors" title="View Results">
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    )}
                    <button onClick={() => handleDelete(e.id)} className="p-1.5 text-gray-600 hover:text-red-400 hover:bg-red-900/30 rounded transition-colors" title="Delete">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {evaluations.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-600">
                  No evaluations yet. Add a model first, then create an evaluation.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
