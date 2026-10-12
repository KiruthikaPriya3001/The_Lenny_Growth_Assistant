import { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatView from './features/chat/ChatView'
import KnowledgeBase from './features/knowledge-base/KnowledgeBase'
import WritingStudio from './features/writing-studio/WritingStudio'
import ArtifactLibrary from './features/artifacts/ArtifactLibrary'
import Settings from './features/settings/Settings'
import type { AppState } from './types'

export default function App() {
  const [state, setState] = useState<AppState>({
    activeConversationId: null,
    activeArtifactId: null,
    sidebarOpen: true,
    activeView: 'chat',
  })

  const setConversation = useCallback((id: string | null) => {
    setState(s => ({ ...s, activeConversationId: id, activeView: 'chat' }))
  }, [])

  const setWritingConversation = useCallback((id: string) => {
    setState(s => ({ ...s, activeConversationId: id }))
  }, [])

  const setView = useCallback((view: AppState['activeView']) => {
    setState(s => ({ ...s, activeView: view }))
  }, [])

  const setArtifact = useCallback((id: string | null) => {
    setState(s => ({ ...s, activeArtifactId: id }))
  }, [])

  const toggleSidebar = useCallback(() => {
    setState(s => ({ ...s, sidebarOpen: !s.sidebarOpen }))
  }, [])

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--color-bg)' }}>
      {/* Left sidebar */}
      {state.sidebarOpen && (
        <Sidebar
          activeView={state.activeView}
          activeConversationId={state.activeConversationId}
          onSelectConversation={setConversation}
          onNewChat={() => setConversation(null)}
          onSelectView={setView}
        />
      )}

      {/* Main content area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        {state.activeView === 'chat' && (
          <ChatView
            conversationId={state.activeConversationId}
            onConversationCreated={setConversation}
            onArtifactCreated={setArtifact}
            onToggleSidebar={toggleSidebar}
            sidebarOpen={state.sidebarOpen}
          />
        )}
        {state.activeView === 'knowledge' && (
          <KnowledgeBase onToggleSidebar={toggleSidebar} sidebarOpen={state.sidebarOpen} />
        )}
        {state.activeView === 'writing' && (
          <WritingStudio
            conversationId={state.activeConversationId}
            onConversationCreated={setWritingConversation}
            onToggleSidebar={toggleSidebar}
            sidebarOpen={state.sidebarOpen}
          />
        )}
        {state.activeView === 'artifacts' && (
          <ArtifactLibrary
            conversationId={state.activeConversationId}
            onToggleSidebar={toggleSidebar}
            sidebarOpen={state.sidebarOpen}
          />
        )}
        {state.activeView === 'settings' && (
          <Settings onToggleSidebar={toggleSidebar} sidebarOpen={state.sidebarOpen} />
        )}
      </div>
    </div>
  )
}
