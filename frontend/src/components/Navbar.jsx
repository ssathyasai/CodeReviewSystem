import React from 'react'
import { ShieldCheck, LayoutDashboard, FileCode, History, Github, Activity, Sparkles } from 'lucide-react'

export default function Navbar({ activeTab, setActiveTab, systemStatus }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'scanner', label: 'Code Scanner', icon: FileCode },
    { id: 'history', label: 'Audit History', icon: History },
    { id: 'github', label: 'GitHub Webhook', icon: Github },
  ]

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 bg-[#070A11]/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo */}
          <div className="flex items-center space-x-3 cursor-pointer group" onClick={() => setActiveTab('dashboard')}>
            <div className="p-2.5 bg-gradient-to-br from-blue-600/30 to-purple-600/30 text-cyan-400 rounded-xl border border-cyan-500/30 group-hover:border-cyan-400/60 shadow-glow-blue transition-all">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-extrabold tracking-tight gradient-text">
                  Hybrid Code Intelligence
                </h1>
                <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px] font-mono border border-blue-500/20">v2.0</span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono flex items-center space-x-1">
                <span>Enterprise Security & Policy Auditor</span>
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex space-x-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800/80">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = activeTab === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`relative flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600/30 to-indigo-600/30 text-white border border-blue-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                  {isActive && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-gradient-to-r from-cyan-400 to-indigo-400 rounded-full"></span>
                  )}
                </button>
              )
            })}
          </nav>

          {/* System Status Indicators */}
          <div className="flex items-center space-x-3 text-xs font-mono">
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-medium text-[11px]">MongoDB Atlas</span>
            </div>
            <div className={`hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-full ${
              systemStatus?.groq_working
                ? 'bg-purple-500/10 text-purple-300 border border-purple-500/25'
                : 'bg-amber-500/10 text-amber-300 border border-amber-500/25'
            }`}>
              <Activity className="w-3.5 h-3.5" />
              <span className="font-medium text-[11px]">{systemStatus?.groq_working ? 'Groq Llama 3.3 Active' : 'Fallback Engine'}</span>
            </div>
          </div>

        </div>
      </div>
    </header>
  )
}
