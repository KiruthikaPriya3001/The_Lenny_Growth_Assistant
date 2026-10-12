import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { BookOpen, RefreshCw, Search, ExternalLink, Database, Menu, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'
import { api } from '../../lib/api'
import type { IngestionJob } from '../../types'

interface KnowledgeBaseProps {
  onToggleSidebar: () => void
  sidebarOpen: boolean
}

export default function KnowledgeBase({ onToggleSidebar }: KnowledgeBaseProps) {
  const [search, setSearch] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)

  const { data: sources, refetch: refetchSources } = useQuery({
    queryKey: ['sources', search],
    queryFn: () => api.listSources(1, 30, search || undefined),
  })

  const { data: jobs, refetch: refetchJobs } = useQuery({
    queryKey: ['ingestion-jobs'],
    queryFn: api.listIngestionJobs,
    refetchInterval: jobId ? 3000 : 30000,
  })

  const { data: jobStatus } = useQuery<IngestionJob | null>({
    queryKey: ['ingestion-job', jobId],
    queryFn: () => jobId ? api.getIngestionJob(jobId) : null,
    enabled: !!jobId,
    refetchInterval: jobId ? 2000 : false,
  })

  // Handle done/failed via side effect based on jobStatus
  if (jobStatus && (jobStatus.status === 'done' || jobStatus.status === 'failed') && jobId) {
    setJobId(null)
    refetchSources()
    refetchJobs()
  }

  const startIngestion = useMutation({
    mutationFn: api.startIngestion,
    onSuccess: (job) => {
      setJobId(job.id)
      refetchJobs()
    },
  })

  const activeJob: IngestionJob | undefined = jobs?.find((j: IngestionJob) => j.status === 'running') || jobStatus || undefined
  const lastDoneJob: IngestionJob | undefined = jobs?.find((j: IngestionJob) => j.status === 'done')
  const isRunning = activeJob?.status === 'running' || startIngestion.isPending

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
        <BookOpen size={16} color="var(--color-accent)" />
        <h1 style={{ fontSize: 15, fontWeight: 700, margin: 0, letterSpacing: '-0.01em' }}>Knowledge Base</h1>
        <div style={{ flex: 1 }} />
        <button
          className="btn btn-primary btn-sm"
          onClick={() => startIngestion.mutate()}
          disabled={isRunning}
        >
          {isRunning ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
          {isRunning ? 'Ingesting…' : 'Ingest Transcripts'}
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
          {[
            { label: 'Sources Indexed', value: sources?.total ?? '–', icon: Database },
            { label: 'Last Ingestion', value: lastDoneJob?.completed_at ? new Date(lastDoneJob.completed_at).toLocaleDateString() : 'Never', icon: CheckCircle },
            { label: 'Chunks Created', value: lastDoneJob?.chunks_created ?? '–', icon: RefreshCw },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="surface" style={{ padding: '14px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <Icon size={14} color="var(--color-text-faint)" />
                <span style={{ fontSize: 11, color: 'var(--color-text-faint)', fontWeight: 500 }}>{label}</span>
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Active job progress */}
        {isRunning && activeJob && (
          <div style={{
            background: 'var(--color-accent-light)', border: '1px solid var(--color-accent)',
            borderRadius: 'var(--radius-lg)', padding: '12px 16px', marginBottom: 20,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Loader2 size={14} color="var(--color-accent)" className="animate-spin" />
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-accent)' }}>
                Ingesting transcripts…
              </span>
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--color-text-muted)', marginBottom: 8 }}>
              {activeJob.processed_files ?? 0} / {activeJob.total_files ?? '?'} files processed
              · {activeJob.sources_created ?? 0} sources created
              · {activeJob.chunks_created ?? 0} chunks indexed
            </div>
            {activeJob.total_files && (
              <div style={{ height: 6, background: 'white', borderRadius: 99, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', background: 'var(--color-accent)', borderRadius: 99,
                  width: `${Math.min(100, ((activeJob.processed_files ?? 0) / activeJob.total_files) * 100)}%`,
                  transition: 'width 0.5s',
                }} />
              </div>
            )}
          </div>
        )}

        {/* Ingestion setup state */}
        {!isRunning && (sources?.total ?? 0) === 0 && (
          <div style={{
            background: '#fffbeb', border: '1px solid #fde68a',
            borderRadius: 'var(--radius-lg)', padding: '16px 20px', marginBottom: 20,
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <AlertTriangle size={16} color="#d97706" style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#92400e', marginBottom: 4 }}>
                  No transcripts indexed yet
                </div>
                <div style={{ fontSize: 12.5, color: '#78350f', lineHeight: 1.6 }}>
                  Click "Ingest Transcripts" to download and index transcripts from the official{' '}
                  <a href="https://github.com/LennysNewsletter/lennys-newsletterpodcastdata" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-accent)' }}>
                    LennysNewsletter GitHub repository
                  </a>.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Search */}
        <div style={{ marginBottom: 16, position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-faint)' }} />
          <input
            className="input"
            placeholder="Search sources by title or guest name…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ paddingLeft: 32 }}
          />
        </div>

        {/* Sources list */}
        <div>
          {sources?.items.map(source => (
            <div key={source.id} className="surface" style={{ padding: '12px 14px', marginBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', marginTop: 5,
                  background: source.source_type === 'podcast' ? 'var(--color-accent)' : 'var(--color-success)',
                  flexShrink: 0,
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600, marginBottom: 2 }}>{source.title}</div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 11.5, color: 'var(--color-text-faint)', flexWrap: 'wrap' }}>
                    {source.author && <span>by {source.author}</span>}
                    {source.date_published && <span>{source.date_published}</span>}
                    <span>{source.chunk_count} chunks</span>
                    {source.word_count && <span>{source.word_count.toLocaleString()} words</span>}
                    <span className={`badge ${source.source_type === 'podcast' ? 'badge-grounded' : 'badge-partial'}`} style={{ padding: '1px 6px', fontSize: 10 }}>
                      {source.source_type}
                    </span>
                  </div>
                </div>
                {source.canonical_url && (
                  <a href={source.canonical_url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-icon btn-sm">
                    <ExternalLink size={12} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
