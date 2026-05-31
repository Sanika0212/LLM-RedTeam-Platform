import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import type { LLMModel } from '../types'

const PROVIDERS = ['openai', 'anthropic', 'huggingface', 'custom']

export default function Models() {
  const [models, setModels] = useState<LLMModel[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', provider: 'openai', model_id: '', description: '' })
  const [error, setError] = useState('')

  const load = () => api.getModels().then(setModels).catch(console.error)

  useEffect(() => { load() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.createModel(form)
      setForm({ name: '', provider: 'openai', model_id: '', description: '' })
      setShowForm(false)
      load()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this model?')) return
    await api.deleteModel(id)
    load()
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Models</h1>
          <p className="text-gray-500 mt-1">Register and manage LLMs for evaluation</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors">
          <Plus className="w-4 h-4" /> Add Model
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name</label>
              <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} required className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-red-500" placeholder="GPT-4 Turbo" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Provider</label>
              <select value={form.provider} onChange={e => setForm({...form, provider: e.target.value})} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-red-500">
                {PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Model ID</label>
              <input value={form.model_id} onChange={e => setForm({...form, model_id: e.target.value})} required className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-red-500" placeholder="gpt-4-turbo-preview" />
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {models.map(m => (
          <div key={m.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-white font-semibold">{m.name}</h3>
                <p className="text-xs text-gray-500 mt-0.5">{m.provider} / {m.model_id}</p>
              </div>
              <button onClick={() => handleDelete(m.id)} className="text-gray-600 hover:text-red-400 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            {m.description && <p className="text-sm text-gray-400">{m.description}</p>}
            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-800">
              <div>
                <p className="text-xs text-gray-500">Safety</p>
                <p className="text-sm font-medium text-green-400">{(m.safety_score * 100).toFixed(1)}%</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Robustness</p>
                <p className="text-sm font-medium text-blue-400">{(m.robustness_score * 100).toFixed(1)}%</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Evals</p>
                <p className="text-sm font-medium text-white">{m.total_evaluations}</p>
              </div>
            </div>
          </div>
        ))}
        {models.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-600">
            No models registered. Click "Add Model" to get started.
          </div>
        )}
      </div>
    </div>
  )
}
