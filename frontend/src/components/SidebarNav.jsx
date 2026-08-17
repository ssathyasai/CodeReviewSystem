import React from 'react'
import { ShieldCheck, LayoutDashboard, FileCode, History, Github, Activity, Sparkles, Terminal, ChevronRight, Zap, User, LogOut, LogIn } from 'lucide-react'

export default function SidebarNav({ activeTab, setActiveTab, systemStatus, currentUser, onOpenAuth, onLogout }) {
  const menuItems = [
    { id: 'dashboard', label: 'Overview', icon: LayoutDashboard, badge: 'Live' },
    { id: 'scanner', label: 'Code Auditor', icon: FileCode, badge: 'SAST/DAST' },
    { id: 'history', label: 'Audit Logs', icon: History, badge: 'MongoDB' },
    { id: 'github', label: 'Webhook Projects', icon: Github, badge: 'Live Tracker' },
  ]

  return (
    <aside className="w-64 cyber-sidebar flex flex-col justify-between hidden md:flex shrink-0 h-screen sticky top-0 border-r border-slate-800/80">
      <div className="p-6 space-y-8">
        
        {/* Brand Header */}
        <div className="flex items-center space-x-3 cursor-pointer group" onClick={() => setActiveTab('dashboard')}>
          <div className="p-3 bg-gradient-to-br from-cyan-500/20 via-blue-600/20 to-purple-600/20 text-cyan-400 rounded-2xl border border-cyan-500/30 group-hover:border-cyan-400/60 glow-cyan transition-all">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base font-extrabold tracking-tight font-heading gradient-text-cyan">
              CodeIntelligence
            </h1>
            <p className="text-[10px] text-slate-400 font-mono tracking-widest uppercase">AI Security Agent</p>
          </div>
        </div>

        {/* Quick Launch Button */}
        <button
          onClick={() => setActiveTab('scanner')}
          className="w-full py-3 px-4 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-extrabold text-xs font-heading flex items-center justify-between shadow-glow-cyan transition-all transform hover:-translate-y-0.5"
        >
          <div className="flex items-center space-x-2">
            <Zap className="w-4 h-4 fill-current" />
            <span>Launch Live Scan</span>
          </div>
          <ChevronRight className="w-4 h-4" />
        </button>

        {/* Navigation Menu */}
        <nav className="space-y-1.5">
          <div className="px-3 pb-2 text-[10px] font-mono tracking-widest text-slate-500 uppercase">MAIN WORKSPACE</div>
          {menuItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-3 rounded-2xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-cyan-500/15 via-blue-500/10 to-transparent text-white border border-cyan-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-800 text-slate-400 border border-slate-700'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* User Profile & Footer Status Panel */}
      <div className="p-4 m-4 space-y-3">
        {/* User Account Card */}
        {currentUser ? (
          <div className="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2.5 overflow-hidden">
              <div className="p-2 rounded-xl bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30">
                <User className="w-4 h-4" />
              </div>
              <div className="truncate">
                <p className="text-xs font-bold text-white truncate font-heading">{currentUser.username}</p>
                <p className="text-[10px] text-slate-400 font-mono truncate">{currentUser.email}</p>
              </div>
            </div>
            <button
              onClick={onLogout}
              title="Sign Out"
              className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-rose-500/10 transition-all shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="w-full py-2.5 px-3 rounded-2xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-cyan-400 font-semibold text-xs font-mono flex items-center justify-center space-x-2 transition-all"
          >
            <LogIn className="w-4 h-4" />
            <span>Sign In Account</span>
          </button>
        )}

        {/* Status System Info */}
        <div className="p-3 rounded-2xl bg-slate-900/50 border border-slate-800/60 space-y-2 font-mono text-[10px]">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Database:</span>
            <span className="text-emerald-400 font-bold flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>MongoDB</span>
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Groq LLM:</span>
            <span className={`font-bold ${systemStatus?.groq_working ? 'text-purple-400' : 'text-amber-400'}`}>
              {systemStatus?.groq_working ? 'Llama 3.3' : 'Fallback'}
            </span>
          </div>
        </div>
      </div>
    </aside>
  )
}
