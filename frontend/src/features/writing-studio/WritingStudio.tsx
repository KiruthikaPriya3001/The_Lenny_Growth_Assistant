import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PenTool, Wand2, RefreshCw, Copy, Download, Menu, CheckCircle, Loader2, AlertCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../../lib/api'
import type { Artifact } from '../../types'

interface WritingStudioProps {
  conversationId: string | null
  onConversationCreated: (id: string) => void
  onToggleSidebar: () => void
  sidebarOpen: boolean
}

export default function WritingStudio({ conversationId, onConversationCreated, onToggleSidebar }: WritingStudioProps) {
  const queryClient = useQueryClient()
  const [thesis, setThesis] = useState('')
  const [audience, setAudience] = useState('product managers and growth practitioners')
  const [artifact, setArtifact] = useState<Artifact | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!conversationId) {
        // Create a conversation first
        const conv = await api.createSession(thesis.slice(0, 60))
        return api.generateEssay(conv.id, thesis, audience)
      }
      return api.generateEssay(conversationId, thesis, audience)
    },
    onSuccess: (data) => {
      setArtifact(data)
      setError(null)
      onConversationCreated(data.conversation_id)
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      queryClient.invalidateQueries({ queryKey: ['artifacts', data.conversation_id] })
    },
    onError: (err: any) => {
      setError(err.message || 'Essay generation failed')
    },
  })

  const copy = () => {
    if (!artifact) return
    navigator.clipboard.writeText(artifact.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const download = () => {
    if (!artifact) return
    const blob = new Blob([artifact.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${artifact.title.replace(/[^a-z0-9]/gi, '-').toLowerCase()}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const wordCount = artifact ? artifact.content.split(/\s+/).filter(Boolean).length : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid var(--color-border)',
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'var(--color-surface)',
      }}>
        <button className="btn btn-ghost btn-icon btn-sm" onClick={onToggleSidebar}>
          <Menu size={15} />
        </button>
        <PenTool size={16} color="var(--color-accent)" />
        <h1 style={{ fontSize: 15, fontWeight: 700, margin: 0, letterSpacing: '-0.01em' }}>Writing Studio</h1>
        <div style={{ fontSize: 11.5, color: 'var(--color-text-faint)', marginLeft: 4 }}>Ship 30 for 30 essays</div>
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left: input panel */}
        <div style={{
          width: 300, borderRight: '1px solid var(--color-border)',
          padding: 20, overflowY: 'auto', background: 'var(--color-surface)',
        }}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', display: 'block', marginBottom: 6 }}>
              Essay Topic / Thesis
            </label>
            <textarea
              className="textarea"
              placeholder="e.g. 'What the transcripts say about retention strategies for early-stage products'"
              value={thesis}
              onChange={e => setThesis(e.target.value)}
              rows={4}
              style={{ fontSize: 13 }}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', display: 'block', marginBottom: 6 }}>
              Target Audience
            </label>
            <input
              className="input"
              value={audience}
              onChange={e => setAudience(e.target.value)}
              placeholder="e.g. early-stage founders"
              style={{ fontSize: 13 }}
            />
          </div>

          <div style={{ padding: '10px 12px', background: 'var(--color-surface-2)', borderRadius: 'var(--radius)', marginBottom: 20, fontSize: 12, color: 'var(--color-text-muted)' }}>
            <strong>Ship 30 for 30 style:</strong> Hook → Thesis → Evidence body → Actionable takeaway.
            Target: ~1,250 words, grounded in retrieved transcript evidence.
          </div>

          <button
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={() => generateMutation.mutate()}
            disabled={!thesis.trim() || generateMutation.isPending}
          >
            {generateMutation.isPending
              ? <><Loader2 size={14} className="animate-spin" /> Generating…</>
              : <><Wand2 size={14} /> Generate Essay</>
            }
          </button>

          {error && (
            <div style={{ marginTop: 12, padding: '10px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius)', fontSize: 12.5, color: 'var(--color-error)', display: 'flex', gap: 6 }}>
              <AlertCircle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
              {error}
            </div>
          )}

          {artifact && !generateMutation.isPending && (
            <div style={{ marginTop: 16, padding: '10px 12px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 'var(--radius)', fontSize: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--color-success)', marginBottom: 4 }}>
                <CheckCircle size={12} />
                <strong>Essay generated</strong>
              </div>
              <div style={{ color: 'var(--color-text-muted)' }}>~{wordCount} words</div>
            </div>
          )}
        </div>

        {/* Right: essay preview */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {artifact ? (
            <>
              <div style={{
                padding: '10px 20px', borderBottom: '1px solid var(--color-border)',
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'var(--color-surface)',
              }}>
                <div style={{ flex: 1, fontSize: 13, fontWeight: 600 }}>{artifact.title}</div>
                <span style={{ fontSize: 11, color: 'var(--color-text-faint)' }}>~{wordCount} words</span>
                <button className="btn btn-ghost btn-sm" onClick={() => generateMutation.mutate()}>
                  <RefreshCw size={12} /> Regenerate
                </button>
                <button className="btn btn-ghost btn-icon btn-sm" onClick={copy}>
                  {copied ? <CheckCircle size={13} color="var(--color-success)" /> : <Copy size={13} />}
                </button>
                <button className="btn btn-ghost btn-icon btn-sm" onClick={download}>
                  <Download size={13} />
                </button>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px', maxWidth: 720, margin: '0 auto', width: '100%' }}>
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {artifact.content}
                  </ReactMarkdown>
                </div>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', color: 'var(--color-text-faint)', gap: 12 }}>
              {generateMutation.isPending ? (
                <>
                  <Loader2 size={28} className="animate-spin" color="var(--color-accent)" />
                  <div style={{ fontSize: 14 }}>Writing your essay…</div>
                  <div style={{ fontSize: 12 }}>Retrieving evidence from transcripts</div>
                </>
              ) : (
                <>
                  <PenTool size={32} style={{ opacity: 0.2 }} />
                  <div style={{ fontSize: 14 }}>Enter a thesis and click Generate</div>
                  <div style={{ fontSize: 12 }}>Your ~1,250-word essay will appear here</div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
