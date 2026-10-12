import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Send, Square, Copy, Menu, ChevronDown,
  Sparkles, FileText, Globe, Zap, CheckCircle, AlertCircle, Loader2
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../../lib/api'
import EvidencePanel from '../evidence/EvidencePanel'
import ArtifactViewer from '../artifacts/ArtifactViewer'
import type { Message, Artifact } from '../../types'

interface ChatViewProps {
  conversationId: string | null
  onConversationCreated: (id: string) => void
  onArtifactCreated: (id: string | null) => void
  onToggleSidebar: () => void
  sidebarOpen: boolean
}

const STARTER_PROMPTS = [
  { icon: '🔍', text: 'What do the transcripts say about finding product-market fit?' },
  { icon: '📊', text: 'Compare evidence-backed approaches to user onboarding' },
  { icon: '🧪', text: 'Create a growth experiment brief for improving activation' },
  { icon: '✍️', text: 'Write a 1,250-word essay on retention strategies from Lenny\'s guests' },
  { icon: '🚀', text: 'Generate a landing page from this conversation' },
  { icon: '📋', text: 'Create a Decision Brief for improving user activation' },
]

const MODE_OPTIONS = [
  { value: 'standard', label: 'Standard Answer', icon: Sparkles },
  { value: 'decision_brief', label: 'Decision Brief', icon: FileText },
  { value: 'essay', label: 'Ship 30 Essay', icon: Zap },
  { value: 'html_artifact', label: 'HTML Artifact', icon: Globe },
]

function GroundingBadge({ grounding }: { grounding?: string }) {
  if (!grounding) return null
  const map: Record<string, { cls: string; label: string }> = {
    grounded: { cls: 'badge-grounded', label: '✓ Grounded' },
    partial: { cls: 'badge-partial', label: '~ Partially Grounded' },
    ungrounded: { cls: 'badge-ungrounded', label: '○ General Knowledge' },
    declined: { cls: 'badge-declined', label: '✗ Insufficient Evidence' },
  }
  const info = map[grounding] || map.ungrounded
  return <span className={`badge ${info.cls}`}>{info.label}</span>
}

function MessageBubble({
  msg, onViewEvidence
}: {
  msg: Message
  onViewEvidence: (msg: Message) => void
}) {
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (msg.role === 'user') {
    return (
      <div className="animate-slide-in" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <div style={{
          maxWidth: '72%', background: 'var(--color-accent)', color: 'white',
          padding: '10px 14px', borderRadius: '14px 14px 4px 14px',
          fontSize: 14, lineHeight: 1.6,
        }}>
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div className="animate-slide-in" style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
      {/* Avatar */}
      <div style={{
        width: 28, height: 28, borderRadius: '50%', background: 'var(--color-accent-light)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 2,
        border: '1px solid var(--color-accent)',
      }}>
        <Sparkles size={12} color="var(--color-accent)" />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Message content */}
        <div style={{
          background: 'var(--color-surface)', border: '1px solid var(--color-border)',
          borderRadius: '4px 14px 14px 14px', padding: '12px 16px',
          boxShadow: 'var(--shadow-sm)',
        }}>
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
          </div>
        </div>

        {/* Footer: metadata + actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
          <GroundingBadge grounding={msg.grounding} />

          {msg.provider && (
            <span style={{ fontSize: 11, color: 'var(--color-text-faint)' }}>
              {msg.provider} · {msg.model?.split('/').pop() || msg.model}
            </span>
          )}

          {msg.duration_ms && (
            <span style={{ fontSize: 11, color: 'var(--color-text-faint)' }}>
              {(msg.duration_ms / 1000).toFixed(1)}s
            </span>
          )}

          <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
            {msg.sources && msg.sources.length > 0 && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => onViewEvidence(msg)}
                style={{ fontSize: 11.5, gap: 4 }}
              >
                <FileText size={11} />
                {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''}
              </button>
            )}
            <button className="btn btn-ghost btn-sm btn-icon" onClick={copy} title="Copy">
              {copied ? <CheckCircle size={12} color="var(--color-success)" /> : <Copy size={12} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ThinkingBubble() {
  return (
    <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
      <div style={{
        width: 28, height: 28, borderRadius: '50%', background: 'var(--color-accent-light)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        border: '1px solid var(--color-accent)',
      }}>
        <Loader2 size={12} color="var(--color-accent)" className="animate-spin" />
      </div>
      <div style={{
        background: 'var(--color-surface)', border: '1px solid var(--color-border)',
        borderRadius: '4px 14px 14px 14px', padding: '12px 16px', boxShadow: 'var(--shadow-sm)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {[0, 1, 2].map(i => (
            <div key={i} className="animate-pulse" style={{
              width: 6, height: 6, borderRadius: '50%', background: 'var(--color-accent)',
              animationDelay: `${i * 0.15}s`,
            }} />
          ))}
        </div>
        <span style={{ fontSize: 12.5, color: 'var(--color-text-faint)' }}>
          Searching knowledge base…
        </span>
      </div>
    </div>
  )
}

export default function ChatView({
  conversationId, onConversationCreated, onArtifactCreated,
  onToggleSidebar, sidebarOpen: _sidebarOpen
}: ChatViewProps) {
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<string>('standard')
  const [showModeMenu, setShowModeMenu] = useState(false)
  const [isThinking, setIsThinking] = useState(false)
  const [evidenceMsg, setEvidenceMsg] = useState<Message | null>(null)
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const qc = useQueryClient()

  // Load conversation info
  const { data: conversation } = useQuery({
    queryKey: ['session', conversationId],
    queryFn: () => conversationId ? api.getSession(conversationId) : null,
    enabled: !!conversationId,
  })

  // Load messages
  const { data: msgData, refetch: refetchMessages } = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => conversationId ? api.listMessages(conversationId) : null,
    enabled: !!conversationId,
  })

  const messages = msgData?.items || []

  // Load models info for status bar
  const { data: modelsInfo } = useQuery({
    queryKey: ['models'],
    queryFn: api.listModels,
    staleTime: 60_000,
  })

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  const sendMessage = useCallback(async () => {
    const content = input.trim()
    if (!content || isThinking) return
    setInput('')
    setError(null)
    setIsThinking(true)

    try {
      let sessionId = conversationId
      if (!sessionId) {
        const conv = await api.createSession(content.slice(0, 60))
        sessionId = conv.id
        onConversationCreated(sessionId)
      }

      qc.invalidateQueries({ queryKey: ['sessions'] })

      const response = await api.sendMessage(sessionId, content, mode)
      await refetchMessages()

      // If artifact was generated, load it
      if (response.grounding === 'grounded' && mode === 'html_artifact') {
        const artifacts = await api.listSessionArtifacts(sessionId)
        if (artifacts.length > 0) {
          const latest = artifacts[0]
          setActiveArtifact(latest)
          onArtifactCreated(latest.id)
        }
      }

      qc.invalidateQueries({ queryKey: ['sessions'] })
    } catch (err: any) {
      setError(err?.message || 'Failed to send message. Check if the backend is running.')
    } finally {
      setIsThinking(false)
    }
  }, [input, isThinking, conversationId, mode, onConversationCreated, onArtifactCreated, refetchMessages, qc])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const currentMode = MODE_OPTIONS.find(m => m.value === mode) || MODE_OPTIONS[0]
  const ModeIcon = currentMode.icon

  const panelWidth = activeArtifact ? '55%' : evidenceMsg ? '55%' : '100%'

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* ── Main chat column ── */}
      <div style={{ width: panelWidth, display: 'flex', flexDirection: 'column', transition: 'width 0.25s', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{
          padding: '12px 16px', borderBottom: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', gap: 10,
          background: 'var(--color-surface)',
        }}>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onToggleSidebar} title="Toggle sidebar">
            <Menu size={15} />
          </button>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h1 style={{ fontSize: 14, fontWeight: 600, margin: 0, color: 'var(--color-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {conversation?.title || 'New Conversation'}
            </h1>
          </div>

          {/* Mode selector */}
          <div style={{ position: 'relative' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowModeMenu(v => !v)}
              style={{ gap: 5 }}
            >
              <ModeIcon size={12} />
              {currentMode.label}
              <ChevronDown size={12} />
            </button>
            {showModeMenu && (
              <div style={{
                position: 'absolute', top: '110%', right: 0, zIndex: 100,
                background: 'var(--color-surface)', border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)',
                minWidth: 180, overflow: 'hidden', padding: 4,
              }}>
                {MODE_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    className={`sidebar-item ${mode === opt.value ? 'active' : ''}`}
                    onClick={() => { setMode(opt.value); setShowModeMenu(false) }}
                    style={{ fontSize: 13 }}
                  >
                    <opt.icon size={13} />
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 20px 8px' }}>
          {/* Empty state */}
          {!conversationId && messages.length === 0 && (
            <div style={{ maxWidth: 560, margin: '0 auto' }}>
              <div style={{ textAlign: 'center', marginBottom: 32 }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 14, background: 'var(--color-accent)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 14px',
                }}>
                  <Sparkles size={22} color="white" />
                </div>
                <h2 style={{ fontSize: 20, fontWeight: 700, margin: '0 0 8px', letterSpacing: '-0.02em' }}>
                  Lenny Growth Assistant
                </h2>
                <p style={{ fontSize: 14, color: 'var(--color-text-muted)', margin: 0 }}>
                  From podcast wisdom to evidence-backed execution.
                  Ask a question to search 50+ expert transcripts.
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {STARTER_PROMPTS.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(p.text)}
                    style={{
                      padding: '10px 12px', background: 'var(--color-surface)',
                      border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)',
                      textAlign: 'left', cursor: 'pointer', fontSize: 12.5, color: 'var(--color-text)',
                      lineHeight: 1.4, transition: 'all 0.12s',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = 'var(--color-accent)'
                      e.currentTarget.style.background = 'var(--color-accent-light)'
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = 'var(--color-border)'
                      e.currentTarget.style.background = 'var(--color-surface)'
                    }}
                  >
                    <span style={{ marginRight: 6 }}>{p.icon}</span>
                    {p.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map(msg => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              onViewEvidence={setEvidenceMsg}
            />
          ))}

          {isThinking && <ThinkingBubble />}

          {error && (
            <div style={{
              display: 'flex', alignItems: 'flex-start', gap: 8,
              padding: '10px 14px', background: '#fef2f2',
              border: '1px solid #fecaca', borderRadius: 'var(--radius)',
              marginBottom: 16, color: 'var(--color-error)', fontSize: 13.5,
            }}>
              <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <strong>Error: </strong>{error}
                <button className="btn btn-ghost btn-sm" onClick={() => setError(null)} style={{ marginLeft: 8, color: 'var(--color-error)' }}>
                  Dismiss
                </button>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Status bar */}
        <div className="status-bar">
          <span className={`status-dot ${modelsInfo?.models.find(m => m.is_active)?.available ? 'status-dot-green' : 'status-dot-yellow'}`} />
          <span>{modelsInfo?.active_provider || '…'} · {modelsInfo?.active_model?.split(':')[0] || '…'}</span>
          {modelsInfo && <span>·</span>}
          <span>Retrieval: active</span>
        </div>

        {/* Input area */}
        <div style={{
          padding: '10px 14px 14px',
          background: 'var(--color-surface)',
          borderTop: '1px solid var(--color-border)',
        }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', gap: 8 }}>
            <textarea
              ref={inputRef}
              className="textarea"
              placeholder={`Ask about growth, product, or strategy… (${currentMode.label})`}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              style={{ flex: 1, maxHeight: 140 }}
              disabled={isThinking}
            />
            <button
              className="btn btn-primary"
              style={{ height: 38, width: 38, justifyContent: 'center', flexShrink: 0, padding: 0 }}
              onClick={sendMessage}
              disabled={!input.trim() || isThinking}
              aria-label="Send message"
            >
              {isThinking ? <Square size={14} /> : <Send size={14} />}
            </button>
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-text-faint)', marginTop: 5 }}>
            Enter to send · Shift+Enter for newline · Mode: <strong>{currentMode.label}</strong>
          </div>
        </div>
      </div>

      {/* ── Right panel: Evidence or Artifact ── */}
      {(evidenceMsg || activeArtifact) && (
        <div style={{
          flex: 1, borderLeft: '1px solid var(--color-border)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
          background: 'var(--color-bg)',
        }}>
          {activeArtifact ? (
            <ArtifactViewer
              artifact={activeArtifact}
              onClose={() => setActiveArtifact(null)}
              onUpdate={updated => setActiveArtifact(updated)}
            />
          ) : evidenceMsg ? (
            <EvidencePanel
              message={evidenceMsg}
              onClose={() => setEvidenceMsg(null)}
            />
          ) : null}
        </div>
      )}
    </div>
  )
}
