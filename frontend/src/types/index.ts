// ─── API Types ────────────────────────────────────────────────────────────────

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ConversationList {
  items: Conversation[]
  total: number
  page: number
  page_size: number
}

export interface SourceReference {
  chunk_id: string
  source_id: string
  title: string
  author?: string
  url?: string
  excerpt: string
  score: number
  score_label: string
  section?: string
  supports?: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  model?: string
  provider?: string
  status?: string
  grounding?: 'grounded' | 'partial' | 'ungrounded' | 'declined'
  sources?: SourceReference[]
  duration_ms?: number
  input_tokens?: number
  output_tokens?: number
}

export interface MessageList {
  items: Message[]
  total: number
  page: number
  page_size: number
}

export interface Source {
  id: string
  source_type: string
  title: string
  author?: string
  canonical_url?: string
  external_id?: string
  ingested_at: string
  word_count?: number
  date_published?: string
  chunk_count: number
}

export interface SourceList {
  items: Source[]
  total: number
  page: number
  page_size: number
}

export interface IngestionJob {
  id: string
  status: 'pending' | 'running' | 'done' | 'failed'
  started_at: string
  completed_at?: string
  total_files?: number
  processed_files?: number
  failed_files?: number
  sources_created?: number
  chunks_created?: number
  errors?: Array<{ filename?: string; error: string }>
}

export interface Artifact {
  id: string
  conversation_id: string
  artifact_type: string
  title: string
  content: string
  content_format: string
  source_references?: SourceReference[]
  created_at: string
  updated_at: string
}

export interface ModelInfo {
  provider: string
  model_id: string
  display_name: string
  available: boolean
  is_active: boolean
}

export interface ModelsOut {
  active_provider: string
  active_model: string
  models: ModelInfo[]
}

export interface ReadinessCheck {
  status: string
  timestamp: string
  database: string
  llm_provider: string
  ollama_available: boolean
  anthropic_configured: boolean
  sources_indexed: number
  chunks_indexed: number
}

export interface ApiError {
  error_code: string
  message: string
  detail?: string
}

// ─── Frontend-only types ──────────────────────────────────────────────────────

export type MessageMode = 'standard' | 'decision_brief' | 'essay' | 'html_artifact' | 'markdown_artifact'

export interface PendingMessage {
  id: string
  content: string
  role: 'user'
  created_at: string
}

export interface AppState {
  activeConversationId: string | null
  activeArtifactId: string | null
  sidebarOpen: boolean
  activeView: 'chat' | 'knowledge' | 'writing' | 'artifacts' | 'settings'
}
