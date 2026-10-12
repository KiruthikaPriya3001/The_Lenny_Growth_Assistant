import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LayoutTemplate, Menu, FileText, Globe } from 'lucide-react'
import { api } from '../../lib/api'
import ArtifactViewer from './ArtifactViewer'
import type { Artifact } from '../../types'

interface ArtifactLibraryProps {
  conversationId: string | null
  onToggleSidebar: () => void
  sidebarOpen: boolean
}

const TYPE_ICONS: Record<string, any> = {
  html: Globe, markdown: FileText, essay: FileText,
  decision_brief: FileText, experiment_card: FileText,
}

export default function ArtifactLibrary({ conversationId, onToggleSidebar }: ArtifactLibraryProps) {
  const [selected, setSelected] = useState<Artifact | null>(null)

  const { data: artifacts } = useQuery({
    queryKey: ['artifacts', conversationId],
    queryFn: () => conversationId ? api.listSessionArtifacts(conversationId) : Promise.resolve([]),
    enabled: true,
    refetchInterval: 15000,
  })

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* List */}
      <div style={{ width: 280, borderRight: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{
          padding: '12px 16px', borderBottom: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', gap: 10,
          background: 'var(--color-surface)',
        }}>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onToggleSidebar}>
            <Menu size={15} />
          </button>
          <LayoutTemplate size={16} color="var(--color-accent)" />
          <h1 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Artifacts</h1>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
          {!conversationId && (
            <div style={{ padding: '20px 12px', textAlign: 'center', fontSize: 12.5, color: 'var(--color-text-faint)' }}>
              Select a conversation to view its artifacts
            </div>
          )}
          {artifacts?.length === 0 && conversationId && (
            <div style={{ padding: '20px 12px', textAlign: 'center', fontSize: 12.5, color: 'var(--color-text-faint)' }}>
              No artifacts generated yet.
              Generate one from the chat or Writing Studio.
            </div>
          )}
          {artifacts?.map(a => {
            const Icon = TYPE_ICONS[a.artifact_type] || FileText
            return (
              <div
                key={a.id}
                className={`sidebar-item ${selected?.id === a.id ? 'active' : ''}`}
                onClick={() => setSelected(a)}
                style={{ padding: '10px 10px', gap: 8, display: 'flex' }}
              >
                <Icon size={13} style={{ flexShrink: 0 }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.title}
                  </div>
                  <div style={{ fontSize: 10.5, color: 'var(--color-text-faint)' }}>
                    {a.artifact_type} · {new Date(a.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Viewer */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {selected ? (
          <ArtifactViewer
            artifact={selected}
            onClose={() => setSelected(null)}
            onUpdate={updated => setSelected(updated)}
          />
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-faint)', flexDirection: 'column', gap: 12 }}>
            <LayoutTemplate size={32} style={{ opacity: 0.2 }} />
            <div style={{ fontSize: 14 }}>Select an artifact to preview</div>
          </div>
        )}
      </div>
    </div>
  )
}
