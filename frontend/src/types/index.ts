export interface LLMModel {
  id: number
  name: string
  provider: string
  model_id: string
  description: string
  safety_score: number
  robustness_score: number
  total_evaluations: number
}

export interface Evaluation {
  id: number
  name: string
  description: string
  model_id: number
  eval_type: string
  status: string
  total_prompts: number
  completed_prompts: number
  safety_score: number
  robustness_score: number
  jailbreak_rate: number
  hallucination_rate: number
  created_at: string | null
  completed_at: string | null
}

export interface EvaluationResult {
  id: number
  prompt: string
  response: string
  attack_type: string
  is_jailbroken: number
  toxicity_score: number
  coherence_score: number
  refusal_detected: number
}

export interface AttackPrompt {
  id: number
  category: string
  subcategory: string
  prompt: string
  severity: string
  description: string
  expected_behavior: string
  tags: string[]
}

export interface Stats {
  total_evaluations: number
  completed_evaluations: number
  average_safety_score: number
  average_jailbreak_rate: number
  average_robustness_score: number
  total_models: number
  total_attack_prompts: number
}
