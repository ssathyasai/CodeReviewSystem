import React, { useState, useEffect } from 'react'
import SidebarNav from './components/SidebarNav'
import Dashboard from './components/Dashboard'
import Scanner from './components/Scanner'
import ScanHistory from './components/ScanHistory'
import GitHubSettings from './components/GitHubSettings'
import AuthModal from './components/AuthModal'
import { ShieldCheck, LayoutDashboard, FileCode, History, Github, Activity, User, LogOut, LogIn } from 'lucide-react'
import axios from 'axios'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [systemStatus, setSystemStatus] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)
  const [isAuthOpen, setIsAuthOpen] = useState(false)

  useEffect(() => {
    fetchSystemStatus()
    // Load stored user session
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      try {
        setCurrentUser(JSON.parse(storedUser))
      } catch (err) {
        console.error('Failed to parse user session:', err)
      }
    }
  }, [])

  const fetchSystemStatus = async () => {
    try {
      const res = await axios.get('/llm/status')
      setSystemStatus(res.data)
    } catch (err) {
      console.error('Failed to fetch LLM status:', err)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    setCurrentUser(null)
  }

  const mobileNavItems = [
    { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
    { id: 'scanner', label: 'Auditor', icon: FileCode },
    { id: 'history', label: 'Audit Logs', icon: History },
    { id: 'github', label: 'Webhooks', icon: Github },
  ]

  return (
    <div className="min-h-screen bg-[#050811] text-slate-100 flex flex-col md:flex-row">
      {/* Desktop Left Sidebar */}
      <SidebarNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        currentUser={currentUser}
        onOpenAuth={() => setIsAuthOpen(true)}
        onLogout={handleLogout}
      />

      {/* Mobile Top Header */}
      <header className="md:hidden sticky top-0 z-50 glass-header px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-cyan-500/20 text-cyan-400 rounded-xl border border-cyan-500/30">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h1 className="text-sm font-extrabold font-heading gradient-text-cyan">CodeIntelligence</h1>
        </div>

        <div className="flex items-center space-x-2">
          {currentUser ? (
            <button
              onClick={handleLogout}
              title="Logout"
              className="p-2 rounded-xl bg-slate-900 text-slate-300 border border-slate-800 text-xs"
            >
              <LogOut className="w-4 h-4 text-rose-400" />
            </button>
          ) : (
            <button
              onClick={() => setIsAuthOpen(true)}
              className="px-3 py-1.5 rounded-xl bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-mono"
            >
              Sign In
            </button>
          )}

          <nav className="flex space-x-1">
            {mobileNavItems.map((item) => {
              const Icon = item.icon
              const isActive = activeTab === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`p-2 rounded-xl text-xs font-semibold ${
                    isActive ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      {/* Main Workbench Workspace */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Top Header Status Strip */}
        <div className="hidden md:flex items-center justify-between px-8 py-4 border-b border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
            <span>Workspace /</span>
            <span className="text-cyan-400 font-bold uppercase">{activeTab}</span>
          </div>

          <div className="flex items-center space-x-4 text-xs font-mono">
            {currentUser ? (
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                <User className="w-3.5 h-3.5" />
                <span>Account: <strong>{currentUser.username}</strong></span>
              </div>
            ) : (
              <button
                onClick={() => setIsAuthOpen(true)}
                className="px-3.5 py-1.5 rounded-full bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 font-bold transition-all flex items-center space-x-1.5"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In / Create Account</span>
              </button>
            )}

            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>MongoDB Atlas Cloud</span>
            </div>
          </div>
        </div>

        {/* Content Workspace Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-8">
          {activeTab === 'dashboard' && <Dashboard setActiveTab={setActiveTab} currentUser={currentUser} />}
          {activeTab === 'scanner' && <Scanner currentUser={currentUser} />}
          {activeTab === 'history' && <ScanHistory currentUser={currentUser} />}
          {activeTab === 'github' && <GitHubSettings currentUser={currentUser} />}
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-800/80 py-4 mt-auto bg-slate-950/40">
          <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-500 font-mono">
            Enterprise Multi-User Security Agent &bull; Powered by MongoDB Atlas & React &bull; OWASP Compliant
          </div>
        </footer>
      </div>

      {/* User Auth Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onLoginSuccess={(user) => setCurrentUser(user)}
      />
    </div>
  )
}
