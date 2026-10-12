import { useQuery } from '@tanstack/react-query'
import { Settings as SettingsIcon, Menu, Shield, ExternalLink, CheckCircle, XCircle } from 'lucide-react'
import { api } from '../../lib/api'

interface SettingsProps {
  onToggleSidebar: () => void
  sidebarOpen: boolean
}

function StatusRow({ label, ok, detail }: { label: string; ok: boolean; detail?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid var(--color-border)' }}>
      {ok
        ? <CheckCircle size={14} color="var(--color-success)" />
        : <XCircle size={14} color="var(--color-error)" />
      }
      <span style={{ fontSize: 13.5, fontWeight: 500, flex: 1 }}>{label}</span>
      {detail && <span style={{ fontSize: 12, color: 'var(--color-text-faint)' }}>{detail}</span>}
    </div>
  )
}

export default function Settings({ onToggleSidebar }: SettingsProps) {
  const { data: readiness } = useQuery({
    queryKey: ['readiness'],
    queryFn: api.ready,
    refetchInterval: 30_000,
  })

  const { data: models } = useQuery({
    queryKey: ['models'],
    queryFn: api.listModels,
    staleTime: 60_000,
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid var(--color-border)',
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'var(--color-surface)',
      }}>
        <button className="btn btn-ghost btn-icon btn-sm" onClick={onToggleSidebar}>
          <Menu size={15} />
        </button>
        <SettingsIcon size={16} color="var(--color-accent)" />
        <h1 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Settings</h1>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        <div style={{ maxWidth: 600 }}>
          {/* System status */}
          <section style={{ marginBottom: 28 }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: 'var(--color-text-faint)', textTransform: 'uppercase', marginBottom: 12 }}>
              System Status
            </h2>
            <div className="surface" style={{ padding: '4px 16px' }}>
              <StatusRow
                label="Database (PostgreSQL)"
                ok={readiness?.database === 'ok'}
                detail={readiness?.database}
              />
              <StatusRow
                label="Ollama (Local LLM)"
                ok={readiness?.ollama_available ?? false}
                detail={readiness?.ollama_available ? 'Available' : 'Not running — run: ollama serve'}
              />
              <StatusRow
                label="Anthropic API"
                ok={readiness?.anthropic_configured ?? false}
                detail={readiness?.anthropic_configured ? 'Configured' : 'Not configured — set ANTHROPIC_API_KEY in .env'}
              />
            </div>
          </section>

          {/* Active model */}
          <section style={{ marginBottom: 28 }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: 'var(--color-text-faint)', textTransform: 'uppercase', marginBottom: 12 }}>
              Model Providers
            </h2>
            <div className="surface" style={{ padding: '4px 16px' }}>
              {models?.models.map(m => (
                <div key={m.provider} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid var(--color-border)' }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                    background: m.available ? 'var(--color-success)' : 'var(--color-text-faint)',
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 500 }}>{m.display_name}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--color-text-faint)' }}>{m.model_id}</div>
                  </div>
                  {m.is_active && (
                    <span className="badge badge-grounded">Active</span>
                  )}
                  {!m.available && (
                    <span className="badge badge-ungrounded">Unavailable</span>
                  )}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10, fontSize: 12, color: 'var(--color-text-faint)', lineHeight: 1.6 }}>
              To switch providers, set <code style={{ background: 'var(--color-surface-2)', padding: '1px 4px', borderRadius: 3 }}>LLM_PROVIDER</code> in your{' '}
              <code style={{ background: 'var(--color-surface-2)', padding: '1px 4px', borderRadius: 3 }}>.env</code> file.
              Never switch silently from local to cloud providers.
            </div>
          </section>

          {/* Knowledge base stats */}
          <section style={{ marginBottom: 28 }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: 'var(--color-text-faint)', textTransform: 'uppercase', marginBottom: 12 }}>
              Knowledge Base
            </h2>
            <div className="surface" style={{ padding: '12px 16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-faint)', marginBottom: 2 }}>Sources indexed</div>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{readiness?.sources_indexed ?? '–'}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-faint)', marginBottom: 2 }}>Chunks indexed</div>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{readiness?.chunks_indexed ?? '–'}</div>
                </div>
              </div>
            </div>
          </section>

          {/* Security notes */}
          <section style={{ marginBottom: 28 }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: 'var(--color-text-faint)', textTransform: 'uppercase', marginBottom: 12 }}>
              Security Notes
            </h2>
            <div className="surface" style={{ padding: '14px 16px', fontSize: 13, color: 'var(--color-text-muted)', lineHeight: 1.7 }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                <Shield size={14} color="var(--color-success)" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>API keys and secrets are never sent to the frontend or logged in server output.</div>
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                <Shield size={14} color="var(--color-success)" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>HTML artifacts render in sandboxed iframes with scripts disabled.</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Shield size={14} color="var(--color-success)" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>User authentication is not implemented — this is a single-user local installation.</div>
              </div>
            </div>
          </section>

          {/* Links */}
          <section>
            <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: 'var(--color-text-faint)', textTransform: 'uppercase', marginBottom: 12 }}>
              Resources
            </h2>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {[
                { label: 'API Docs', href: '/api/docs' },
                { label: 'LennysData.com', href: 'https://lennysdata.com' },
                { label: 'Transcript Repo', href: 'https://github.com/LennysNewsletter/lennys-newsletterpodcastdata' },
              ].map(({ label, href }) => (
                <a key={label} href={href} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
                  <ExternalLink size={11} />
                  {label}
                </a>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
