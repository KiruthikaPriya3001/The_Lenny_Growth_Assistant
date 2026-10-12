import { useState } from 'react'
import { X, ExternalLink, ChevronDown, ChevronRight, Info } from 'lucide-react'
import type { Message, SourceReference } from '../../types'

interface EvidencePanelProps {
  message: Message
  onClose: () => void
}

function EvidenceCard({ source }: { source: SourceReference }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="evidence-card" style={{ marginBottom: 8 }}>
      <div className="evidence-header" onClick={() => setExpanded(v => !v)}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--color-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {source.title}
          </div>
          {source.author && (
            <div style={{ fontSize: 11, color: 'var(--color-text-faint)', marginTop: 1 }}>
              {source.author}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            fontSize: 10.5, color: 'var(--color-accent)', background: 'var(--color-accent-light)',
            padding: '2px 6px', borderRadius: 99, fontWeight: 500,
          }}>
            {(source.score * 100).toFixed(0)}%
          </div>
          {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </div>
      </div>

      {expanded && (
        <div className="evidence-body animate-slide-in">
          {source.section && (
            <div style={{ fontSize: 11, color: 'var(--color-accent)', marginBottom: 6, fontWeight: 500 }}>
              § {source.section}
            </div>
          )}
          <p style={{ margin: '0 0 8px', fontStyle: 'italic', color: 'var(--color-text-muted)' }}>
            "{source.excerpt}"
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {source.url && (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--color-accent)' }}
              >
                <ExternalLink size={10} />
                View source
              </a>
            )}
            <span style={{ fontSize: 10.5, color: 'var(--color-text-faint)' }}>
              {source.score_label}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function EvidencePanel({ message, onClose }: EvidencePanelProps) {
  const sources = message.sources || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '12px 14px', borderBottom: '1px solid var(--color-border)',
        display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--color-surface)',
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Evidence Trail</div>
          <div style={{ fontSize: 11, color: 'var(--color-text-faint)' }}>
            {sources.length} source{sources.length !== 1 ? 's' : ''} retrieved
          </div>
        </div>
        <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}>
          <X size={14} />
        </button>
      </div>

      {/* Grounding info */}
      {message.grounding && (
        <div style={{
          padding: '8px 14px', background: 'var(--color-surface-2)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', gap: 6, fontSize: 12,
        }}>
          <Info size={12} color="var(--color-text-faint)" />
          <span style={{ color: 'var(--color-text-muted)' }}>
            Answer is <strong>{message.grounding}</strong>
            {message.duration_ms && ` · ${(message.duration_ms / 1000).toFixed(1)}s`}
            {message.input_tokens && ` · ${message.input_tokens} in / ${message.output_tokens} out tokens`}
          </span>
        </div>
      )}

      {/* Sources list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        {sources.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--color-text-faint)', fontSize: 13 }}>
            <div style={{ marginBottom: 8 }}>No sources retrieved for this message.</div>
            <div style={{ fontSize: 12 }}>
              This response is based on general knowledge, not transcript evidence.
            </div>
          </div>
        ) : (
          sources.map(src => <EvidenceCard key={src.chunk_id} source={src} />)
        )}
      </div>

      {/* Footer disclaimer */}
      <div style={{
        padding: '8px 14px', borderTop: '1px solid var(--color-border)',
        fontSize: 10.5, color: 'var(--color-text-faint)', lineHeight: 1.5,
      }}>
        Retrieval scores indicate text similarity, not correctness probability.
        Always verify important claims against original sources.
      </div>
    </div>
  )
}
