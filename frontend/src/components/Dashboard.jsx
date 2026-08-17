import React, { useState, useEffect } from 'react'
import { Shield, AlertTriangle, CheckCircle, Database, Cpu, Zap, ArrowRight, Play, Sparkles, Layers, Github } from 'lucide-react'
import axios from 'axios'

export default function Dashboard({ setActiveTab }) {
  const [stats, setStats] = useState({
    totalScans: 0,
    criticalCount: 0,
    passedCount: 0,
    warningCount: 0
  })
  const [recentScans, setRecentScans] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const scansRes = await axios.get('/scans?limit=10').catch(() => ({ data: { scans: [] } }))
      const scans = scansRes.data.scans || []

      let critical = 0
      let passed = 0
      let warning = 0

      scans.forEach(scan => {
        const dec = scan.verdict?.decision || (scan.can_deploy ? 'APPROVE' : 'BLOCK')
        if (dec === 'BLOCK' || scan.critical_count > 0 || scan.status === 'critical') {
          critical++
        } else if (dec === 'WARN' || scan.status === 'warning') {
          warning++
        } else {
          passed++
        }
      })

      setStats({
        totalScans: scans.length,
        criticalCount: critical,
        passedCount: passed,
        warningCount: warning
      })
      setRecentScans(scans)
    } catch (err) {
      console.error('Error fetching dashboard data:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl glass-panel p-8 md:p-10 border border-slate-700/50 bg-gradient-to-r from-slate-900/90 via-indigo-950/40 to-slate-900/90 shadow-2xl">
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-600/15 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-purple-600/15 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 max-w-3xl space-y-5">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/25 text-cyan-400 text-xs font-mono">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
            <span>Hybrid Static (SAST) & Dynamic (DAST) AI Governance Platform</span>
          </div>

          <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Enterprise Automated Code Security & Compliance Auditor
          </h2>

          <p className="text-slate-300 text-sm leading-relaxed max-w-2xl">
            Real-time multi-engine reviewer scanning Python AST vulnerability trees, dynamic runtime resource limits, and corporate policy compliance backed by MongoDB Atlas storage.
          </p>

          <div className="pt-3 flex flex-wrap gap-4 items-center">
            <button
              onClick={() => setActiveTab('scanner')}
              className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm rounded-xl shadow-glow-blue transition-all transform hover:-translate-y-0.5"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Launch Live Code Scanner</span>
            </button>

            <button
              onClick={() => setActiveTab('github')}
              className="flex items-center space-x-2 px-5 py-3 bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 font-medium text-sm rounded-xl border border-slate-700/80 transition-all"
            >
              <Github className="w-4 h-4 text-purple-400" />
              <span>Configure GitHub Webhook</span>
              <ArrowRight className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="glass-card p-6 rounded-2xl space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono tracking-wider">DATABASE STORAGE</span>
            <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20 text-blue-400">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white">MongoDB</p>
          <p className="text-xs text-slate-400">Atlas Cloud Collections</p>
        </div>

        <div className="glass-card p-6 rounded-2xl space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono tracking-wider">TOTAL AUDITS</span>
            <div className="p-2 bg-purple-500/10 rounded-xl border border-purple-500/20 text-purple-400">
              <Shield className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white">{stats.totalScans}</p>
          <p className="text-xs text-slate-400">Persisted Audit Reports</p>
        </div>

        <div className="glass-card p-6 rounded-2xl space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono tracking-wider">PASSED VERDICTS</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-emerald-400">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400">{stats.passedCount}</p>
          <p className="text-xs text-slate-400">Approved Builds</p>
        </div>

        <div className="glass-card p-6 rounded-2xl space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono tracking-wider">CRITICAL BLOCKS</span>
            <div className="p-2 bg-rose-500/10 rounded-xl border border-rose-500/20 text-rose-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-rose-400">{stats.criticalCount}</p>
          <p className="text-xs text-slate-400">Deployment Blocked</p>
        </div>
      </div>

      {/* Engine Architecture Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl space-y-3 border-l-4 border-l-cyan-500">
          <div className="flex items-center space-x-3 text-cyan-400">
            <Cpu className="w-5 h-5" />
            <h3 className="font-bold text-white text-base">1. SAST Static Engine</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            AST syntax tree analyzer detecting OWASP Top 10 risks: SQL injection, hardcoded credentials, command injection, weak crypto, and unhandled exceptions.
          </p>
          <div className="pt-1 text-[11px] font-mono text-emerald-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>AST Visitor Active</span>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl space-y-3 border-l-4 border-l-purple-500">
          <div className="flex items-center space-x-3 text-purple-400">
            <Zap className="w-5 h-5" />
            <h3 className="font-bold text-white text-base">2. DAST Dynamic Engine</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Process execution sandbox profiling RAM memory surges, CPU spikes, execution timeouts, infinite loops, and unhandled runtime exceptions.
          </p>
          <div className="pt-1 text-[11px] font-mono text-emerald-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Process Profiler Active</span>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl space-y-3 border-l-4 border-l-indigo-500">
          <div className="flex items-center space-x-3 text-indigo-400">
            <Sparkles className="w-5 h-5" />
            <h3 className="font-bold text-white text-base">3. LLM Governance AI</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Evaluates corporate policy guidelines using Groq Llama 3.3, outputting structured JSON reports with inline auto-fix suggestions.
          </p>
          <div className="pt-1 text-[11px] font-mono text-emerald-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Groq AI Ready</span>
          </div>
        </div>
      </div>

      {/* Recent Audit Timeline Table */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white">Recent Audit History Timeline</h3>
            <p className="text-xs text-slate-400">Latest security audit runs stored in MongoDB</p>
          </div>
          <button
            onClick={() => setActiveTab('history')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-mono font-medium flex items-center space-x-1"
          >
            <span>View All Logs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentScans.length === 0 ? (
          <p className="text-xs text-slate-500 py-8 text-center font-mono">No scans recorded yet. Launch a scan to populate history.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-400 uppercase bg-slate-900/60 font-mono">
                <tr>
                  <th className="px-4 py-3">Scan ID</th>
                  <th className="px-4 py-3">Audit Target</th>
                  <th className="px-4 py-3">Verdict</th>
                  <th className="px-4 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {recentScans.map((scan) => {
                  const decision = scan.verdict?.decision || (scan.status === 'critical' || scan.can_deploy === false ? 'BLOCK' : 'APPROVE')
                  return (
                    <tr key={scan.scan_id || Math.random()} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3 font-mono text-cyan-400 font-medium">{scan.scan_id?.slice(0, 8) || 'N/A'}</td>
                      <td className="px-4 py-3 text-slate-200 font-medium">{scan.file || scan.repository || scan.project_name || 'Uploaded Source Code'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2.5 py-1 rounded-full font-mono text-[10px] font-bold ${
                          decision === 'BLOCK' ? 'badge-critical' : decision === 'WARN' ? 'badge-warning' : 'badge-success'
                        }`}>
                          {decision}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 font-mono">
                        {scan.timestamp ? new Date(scan.timestamp).toLocaleString() : 'Recent'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
