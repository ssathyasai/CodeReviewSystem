import React, { useState, useEffect } from 'react'
import SidebarNav from './components/SidebarNav'
import Dashboard from './components/Dashboard'
import Scanner from './components/Scanner'
import ScanHistory from './components/ScanHistory'
import GitHubSettings from './components/GitHubSettings'
import { ShieldCheck, LayoutDashboard, FileCode, History, Github, Activity } from 'lucide-react'
import axios from 'axios'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [systemStatus, setSystemStatus] = useState(null)

  useEffect(() => {
    fetchSystemStatus()
  }, [])

  const fetchSystemStatus = async () => {
    try {
      const res = await axios.get('/llm/status')
      setSystemStatus(res.data)
    } catch (err) {
      console.error('Failed to fetch LLM status:', err)
    }
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
      <SidebarNav activeTab={activeTab} setActiveTab={setActiveTab} systemStatus={systemStatus} />

      {/* Mobile Top Header */}
      <header className="md:hidden sticky top-0 z-50 glass-header px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-cyan-500/20 text-cyan-400 rounded-xl border border-cyan-500/30">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h1 className="text-sm font-extrabold font-heading gradient-text-cyan">CodeIntelligence</h1>
        </div>

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
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>MongoDB Atlas Cloud</span>
            </div>
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/25">
              <Activity className="w-3.5 h-3.5" />
              <span>OWASP Top 10 Active</span>
            </div>
          </div>
        </div>

        {/* Content Workspace Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-8">
          {activeTab === 'dashboard' && <Dashboard setActiveTab={setActiveTab} />}
          {activeTab === 'scanner' && <Scanner />}
          {activeTab === 'history' && <ScanHistory />}
          {activeTab === 'github' && <GitHubSettings />}
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-800/80 py-4 mt-auto bg-slate-950/40">
          <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-500 font-mono">
            Enterprise Security & Code Intelligence Agent &bull; Powered by MongoDB Atlas, FastAPI & React &bull; OWASP Compliant
          </div>
        </footer>
      </div>
    </div>
  )
}
