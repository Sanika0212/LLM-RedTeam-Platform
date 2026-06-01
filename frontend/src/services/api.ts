const API_BASE = '/api/v1'

function getToken(): string | null {
  return localStorage.getItem('auth_token')
}

export function setToken(token: string) {
  localStorage.setItem('auth_token', token)
}

export function clearToken() {
  localStorage.removeItem('auth_token')
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...options,
  })

  // Auto-logout on 401 — token expired or revoked; reload to show login screen
  if (res.status === 401) {
    clearToken()
    window.location.reload()
    return undefined as T
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || 'Request failed')
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<{ access_token: string; user_id: number; email: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string, full_name: string) =>
    request<{ access_token: string; user_id: number; email: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    }),

  // Models
  getModels: () => request<any[]>('/models/'),
  createModel: (data: any) => request<any>('/models/', { method: 'POST', body: JSON.stringify(data) }),
  deleteModel: (id: number) => request<void>(`/models/${id}`, { method: 'DELETE' }),

  // Evaluations
  getEvaluations: () => request<any[]>('/evaluations/'),
  createEvaluation: (data: any) => request<any>('/evaluations/', { method: 'POST', body: JSON.stringify(data) }),
  getEvaluation: (id: number) => request<any>(`/evaluations/${id}`),
  runEvaluation: (id: number) => request<any>(`/evaluations/${id}/run`, { method: 'POST' }),
  getEvaluationResults: (id: number) => request<any[]>(`/evaluations/${id}/results`),
  deleteEvaluation: (id: number) => request<void>(`/evaluations/${id}`, { method: 'DELETE' }),
  getStats: () => request<any>('/evaluations/stats/summary'),

  // Attack Prompts
  getAttackPrompts: () => request<any[]>('/attack-prompts/'),
  createAttackPrompt: (data: any) => request<any>('/attack-prompts/', { method: 'POST', body: JSON.stringify(data) }),
  seedAttackPrompts: () => request<any>('/attack-prompts/seed', { method: 'POST' }),
  seedResearchDataset: () => request<any>('/attack-prompts/seed-research-dataset', { method: 'POST' }),
  getCategories: () => request<any>('/attack-prompts/categories'),
  deleteAttackPrompt: (id: number) => request<void>(`/attack-prompts/${id}`, { method: 'DELETE' }),

  // Analytics
  getVulnerabilityProfile: (modelId?: number) =>
    request<any>(`/analytics/vulnerability-profile${modelId ? `?model_id=${modelId}` : ''}`),
  getModelComparison: () => request<any>('/analytics/model-comparison'),
  getEvaluationReport: (id: number) => request<any>(`/analytics/evaluation-report/${id}`),
  getCategoryHeatmap: () => request<any>('/analytics/category-heatmap'),
  getEvaluationTimeline: () => request<any>('/analytics/timeline'),
  exportEvaluationCsv: async (id: number): Promise<void> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/analytics/export/${id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    if (res.status === 401) { clearToken(); window.location.reload(); return }
    if (!res.ok) throw new Error('Export failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `evaluation-${id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  },
  getAttackPromptStats: () => request<any>('/analytics/attack-prompts/stats'),

  // Novel Research Endpoints
  getTransferAnalysis: () => request<any>('/analytics/transfer-analysis'),
  getSemanticDriftAnalysis: (evalId: number) => request<any>(`/analytics/semantic-drift/${evalId}`),
  getAdaptiveBudgetSimulation: (budget?: number) =>
    request<any>(`/analytics/adaptive-budget-simulation${budget ? `?budget=${budget}` : ''}`),
  getPairFailureModes: (evalId: number) => request<any>(`/analytics/pair-failure-modes/${evalId}`),
}
