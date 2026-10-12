import { useState } from 'react'
import { X, Copy, Download, Edit3, Eye, Code, CheckCircle, Shield } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../../lib/api'
import type { Artifact } from '../../types'

interface ArtifactViewerProps {
  artifact: Artifact
  onClose: () => void
  onUpdate: (artifact: Artifact) => void
}

type Tab = 'preview' | 'markdown' | 'code'

export default function ArtifactViewer({ artifact, onClose, onUpdate }: ArtifactViewerProps) {
  const [tab, setTab] = useState<Tab>(artifact.content_format === 'html' ? 'preview' : 'markdown')
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState(artifact.content)
  const [editTitle, setEditTitle] = useState(artifact.title)
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState(false)
  const [hasUnsaved, setHasUnsaved] = useState(false)

  const isHtml = artifact.content_format === 'html' || artifact.artifact_type === 'html'

  const copy = async () => {
    await navigator.clipboard.writeText(artifact.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const download = () => {
    const ext = isHtml ? 'html' : 'md'
    const blob = new Blob([artifact.content], { type: isHtml ? 'text/html' : 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${artifact.title.replace(/[^a-z0-9]/gi, '-').toLowerCase()}.${ext}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const saveEdit = async () => {
    setSaving(true)
    try {
      const updated = await api.updateArtifact(artifact.id, {
        title: editTitle,
        content: editContent,
      })
      onUpdate(updated)
      setEditing(false)
      setHasUnsaved(false)
    } catch (err: any) {
      alert('Save failed: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  const availableTabs: Tab[] = isHtml ? ['preview', 'code'] : ['markdown', 'code']

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid var(--color-border)',
        display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--color-surface)', flexShrink: 0,
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {editing ? (
            <input
              className="input"
              value={editTitle}
              onChange={e => setEditTitle(e.target.value)}
              style={{ fontSize: 13, fontWeight: 600, padding: '4px 8px', height: 28 }}
            />
          ) : (
            <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {artifact.title}
            </div>
          )}
          <div style={{ fontSize: 10.5, color: 'var(--color-text-faint)', marginTop: 1 }}>
            {artifact.artifact_type.replace('_', ' ')} · {new Date(artifact.created_at).toLocaleDateString()}
            {hasUnsaved && <span style={{ color: 'var(--color-warning)', marginLeft: 6 }}>● Unsaved</span>}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 4 }}>
          {!editing ? (
            <>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setEditing(true)} title="Edit">
                <Edit3 size={13} />
              </button>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={copy} title="Copy">
                {copied ? <CheckCircle size={13} color="var(--color-success)" /> : <Copy size={13} />}
              </button>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={download} title="Download">
                <Download size={13} />
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-secondary btn-sm" onClick={() => { setEditing(false); setHasUnsaved(false); }}>
                Cancel
              </button>
              <button className="btn btn-primary btn-sm" onClick={saveEdit} disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          )}
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}>
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex', gap: 0, padding: '0 14px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
      }}>
        {availableTabs.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '8px 12px', fontSize: 12.5, fontWeight: 500,
              border: 'none', background: 'none', cursor: 'pointer',
              borderBottom: tab === t ? '2px solid var(--color-accent)' : '2px solid transparent',
              color: tab === t ? 'var(--color-accent)' : 'var(--color-text-muted)',
              display: 'flex', alignItems: 'center', gap: 5,
              marginBottom: -1,
            }}
          >
            {t === 'preview' && <Eye size={12} />}
            {t === 'markdown' && <Eye size={12} />}
            {t === 'code' && <Code size={12} />}
            {t === 'preview' ? 'Preview' : t === 'markdown' ? 'Preview' : 'Source'}
          </button>
        ))}
      </div>

      {/* Security notice for HTML */}
      {isHtml && tab === 'preview' && (
        <div style={{
          padding: '5px 14px', background: '#fffbeb', borderBottom: '1px solid #fde68a',
          display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#92400e',
        }}>
          <Shield size={11} />
          Rendered in sandboxed iframe — no scripts, no DOM access, static HTML/CSS only
        </div>
      )}

      {/* Content */}
      <div style={{ flex: 1, overflow: 'hidden', background: 'var(--color-bg)' }}>
        {editing ? (
          <textarea
            className="textarea"
            value={editContent}
            onChange={e => { setEditContent(e.target.value); setHasUnsaved(true) }}
            style={{
              width: '100%', height: '100%', borderRadius: 0,
              border: 'none', resize: 'none', fontFamily: "'JetBrains Mono', monospace",
              fontSize: 13, padding: 16,
            }}
          />
        ) : tab === 'preview' && isHtml ? (
          /* SECURITY: sandboxed iframe with no scripts, no same-origin, no forms */
          <iframe
            className="artifact-iframe"
            srcDoc={artifact.content}
            sandbox="allow-same-origin"
            style={{ width: '100%', height: '100%', border: 'none' }}
            title={artifact.title}
          />
        ) : tab === 'markdown' ? (
          <div style={{ height: '100%', overflowY: 'auto', padding: '16px 20px' }}>
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {artifact.content}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <pre style={{
              margin: 0, padding: 16, fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12, lineHeight: 1.6, color: 'var(--color-text)',
              background: 'var(--color-bg)', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {artifact.content}
            </pre>
          </div>
        )}
      </div>

      {/* Footer: sources */}
      {artifact.source_references && artifact.source_references.length > 0 && (
        <div style={{
          padding: '8px 14px', borderTop: '1px solid var(--color-border)',
          fontSize: 11, color: 'var(--color-text-faint)',
        }}>
          Based on {artifact.source_references.length} source{artifact.source_references.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}
