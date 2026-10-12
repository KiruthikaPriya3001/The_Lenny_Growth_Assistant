// ─── API Client ───────────────────────────────────────────────────────────────
// All API calls go through this module. Never expose credentials to the frontend.

import type {
  Artifact,
  ConversationList,
  Conversation,
  IngestionJob,
  Message,
  MessageList,
  ModelsOut,
  ReadinessCheck,
  SourceList,
} from '../types'

const BASE = '/api'

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (!res.ok) {
    let errBody: any = {}
    try { errBody = await res.json() } catch {}
    const detail = errBody?.detail || errBody
    const msg = typeof detail === 'object'
      ? detail.message || JSON.stringify(detail)
      : String(detail)
    throw new Error(msg || `HTTP ${res.status}`)
  }

  if (res.status === 204) return undefined as unknown as T
  return res.json()
}

// ─── Health ───────────────────────────────────────────────────────────────────

export const api = {
  ready: (): Promise<ReadinessCheck> => request('/ready'),

  // ─── Sessions ─────────────────────────────────────────────────────────────
  createSession: (title?: string): Promise<Conversation> =>
    request('/sessions', { method: 'POST', body: JSON.stringify({ title }) }),

  listSessions: (page = 1, pageSize = 30): Promise<ConversationList> =>
    request(`/sessions?page=${page}&page_size=${pageSize}`),

  getSession: (id: string): Promise<Conversation> =>
    request(`/sessions/${id}`),

  deleteSession: (id: string): Promise<void> =>
    request(`/sessions/${id}`, { method: 'DELETE' }),

  // ─── Messages ─────────────────────────────────────────────────────────────
  sendMessage: (
    sessionId: string,
    content: string,
    mode?: string,
    provider?: string,
  ): Promise<Message> =>
    request(`/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content, mode, provider }),
    }),

  listMessages: (sessionId: string, page = 1, pageSize = 100): Promise<MessageList> =>
    request(`/sessions/${sessionId}/messages?page=${page}&page_size=${pageSize}`),

  // ─── Sources ──────────────────────────────────────────────────────────────
  listSources: (page = 1, pageSize = 20, search?: string): Promise<SourceList> => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (search) params.set('search', search)
    return request(`/sources?${params}`)
  },

  // ─── Ingestion ────────────────────────────────────────────────────────────
  startIngestion: (): Promise<IngestionJob> =>
    request('/ingestion/jobs', { method: 'POST', body: JSON.stringify({}) }),

  getIngestionJob: (jobId: string): Promise<IngestionJob> =>
    request(`/ingestion/jobs/${jobId}`),

  listIngestionJobs: (): Promise<IngestionJob[]> =>
    request('/ingestion/jobs'),

  // ─── Artifacts ────────────────────────────────────────────────────────────
  createArtifact: (
    conversationId: string,
    artifactType: string,
    prompt: string,
    title?: string,
  ): Promise<Artifact> =>
    request('/artifacts', {
      method: 'POST',
      body: JSON.stringify({ conversation_id: conversationId, artifact_type: artifactType, prompt, title }),
    }),

  getArtifact: (id: string): Promise<Artifact> =>
    request(`/artifacts/${id}`),

  updateArtifact: (id: string, updates: { title?: string; content?: string }): Promise<Artifact> =>
    request(`/artifacts/${id}`, { method: 'PATCH', body: JSON.stringify(updates) }),

  listSessionArtifacts: (sessionId: string): Promise<Artifact[]> =>
    request(`/sessions/${sessionId}/artifacts`),

  // ─── Skills ───────────────────────────────────────────────────────────────
  generateEssay: (
    conversationId: string,
    thesis: string,
    audience?: string,
  ): Promise<Artifact> =>
    request('/skills/ship-30-essay', {
      method: 'POST',
      body: JSON.stringify({ conversation_id: conversationId, thesis, audience }),
    }),

  // ─── Models ───────────────────────────────────────────────────────────────
  listModels: (): Promise<ModelsOut> => request('/models'),
}
