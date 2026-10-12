import { useQuery } from '@tanstack/react-query'
import {
  MessageSquare, Plus, BookOpen, PenTool, LayoutTemplate,
  Settings, Trash2, Bot
} from 'lucide-react'
import { api } from '../lib/api'
import type { AppState } from '../types'

interface SidebarProps {
  activeView: AppState['activeView']
  activeConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewChat: () => void
  onSelectView: (view: AppState['activeView']) => void
}

const NAV = [
  { key: 'chat', label: 'Chat', icon: MessageSquare },
  { key: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
  { key: 'writing', label: 'Writing Studio', icon: PenTool },
  { key: 'artifacts', label: 'Artifact Library', icon: LayoutTemplate },
  { key: 'settings', label: 'Settings', icon: Settings },
] as const

export default function Sidebar({
  activeView, activeConversationId, onSelectConversation, onNewChat, onSelectView
}: SidebarProps) {


  const { data: sessions, refetch } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.listSessions(1, 30),
    refetchInterval: 10_000,
  })

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (!confirm('Delete this conversation?')) return
    await api.deleteSession(id)
    refetch()
    if (activeConversationId === id) onNewChat()
  }

  return (
    <aside style={{
      width: 240, minWidth: 240, height: '100vh', display: 'flex', flexDirection: 'column',
      background: 'var(--color-surface)', borderRight: '1px solid var(--color-border)',
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{ padding: '16px 14px 12px', borderBottom: '1px solid var(--color-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8, background: 'var(--color-accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <Bot size={16} color="white" />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1.2 }}>
              Lenny Growth
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--color-text-faint)', lineHeight: 1 }}>
              powered by GrowthOS
            </div>
          </div>
        </div>
      </div>

      {/* New Chat button */}
      <div style={{ padding: '10px 10px 6px' }}>
        <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={onNewChat}>
          <Plus size={14} /> New Chat
        </button>
      </div>

      {/* Navigation */}
      <nav style={{ padding: '6px 8px' }}>
        {NAV.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            className={`sidebar-item ${activeView === key ? 'active' : ''}`}
            onClick={() => onSelectView(key)}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </nav>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--color-border)', margin: '4px 12px' }} />

      {/* Recent conversations */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '8px 12px 4px', fontSize: 10.5, fontWeight: 600, color: 'var(--color-text-faint)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Recent
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 6px 8px' }}>
          {sessions?.items.length === 0 && (
            <div style={{ padding: '12px 6px', fontSize: 12.5, color: 'var(--color-text-faint)', textAlign: 'center' }}>
              No conversations yet
            </div>
          )}
          {sessions?.items.map(conv => (
            <div
              key={conv.id}
              className={`sidebar-item ${activeConversationId === conv.id && activeView === 'chat' ? 'active' : ''}`}
              onClick={() => { onSelectConversation(conv.id); onSelectView('chat') }}
              style={{ position: 'relative', paddingRight: 30 }}
            >
              <MessageSquare size={12} style={{ flexShrink: 0, opacity: 0.6 }} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, fontSize: 12.5 }}>
                {conv.title || 'New Conversation'}
              </span>
              <button
                className="btn btn-ghost btn-icon"
                style={{ position: 'absolute', right: 2, top: '50%', transform: 'translateY(-50%)', width: 22, height: 22, opacity: 0, padding: 0 }}
                onClick={(e) => handleDelete(e, conv.id)}
                onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                onMouseLeave={e => (e.currentTarget.style.opacity = '0')}
              >
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '8px 12px', borderTop: '1px solid var(--color-border)', fontSize: 11, color: 'var(--color-text-faint)' }}>
        Lenny GrowthOS v1.0
      </div>
    </aside>
  )
}
