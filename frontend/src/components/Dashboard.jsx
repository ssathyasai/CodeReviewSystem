import React, { useState, useEffect } from 'react'
import { ShieldCheck, AlertTriangle, CheckCircle, Database, Cpu, Zap, ArrowRight, Play, Sparkles, Layers, Github, Activity, ShieldAlert, FileCode } from 'lucide-react'
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
        const dec = scan.verdict?.decision || (scan.can_deploy === false || scan.status === 'critical' ? 'BLOCK' : 'APPROVE')
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
      {/* Cyberpunk Shield Hero Card */}
      <div className="relative overflow-hidden rounded-3xl cyber-card p-8 md:p-10 border border-slate-700/60 bg-gradient-to-br from-slate-900/90 via-indigo-950/30 to-slate-950/90 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-cyan-500/20 via-blue-600/10 to-transparent rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-purple-600/20 via-indigo-600/10 to-transparent rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 max-w-3xl space-y-5">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono">
            <Sparkles className="w-3.5 h-3.5 animate-pulse text-cyan-300" />
            <span>Hybrid Static & Dynamic Security Engine</span>
          </div>

          <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight font-heading leading-tight">
            Automated Code Review & OWASP Vulnerability Platform
          </h2>

          <p className="text-slate-300 text-xs sm:text-sm leading-relaxed max-w-2xl">
            Real-time security scanner executing SAST AST analysis, DAST runtime sandbox profiling, and LLM governance review backed by MongoDB Atlas cloud persistence.
          </p>

          <div className="pt-2 flex flex-wrap gap-4 items-center">
            <button
              onClick={() => setActiveTab('scanner')}
              className="flex items-center space-x-2 px-6 py-3.5 bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-extrabold text-xs font-heading rounded-2xl shadow-glow-cyan transition-all transform hover:-translate-y-0.5"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Launch Live Code Scanner</span>
            </button>

            <button
              onClick={() => setActiveTab('github')}
              className="flex items-center space-x-2 px-5 py-3.5 bg-slate-900/90 hover:bg-slate-800 text-slate-200 font-semibold text-xs rounded-2xl border border-slate-700/80 transition-all"
            >
              <Github className="w-4 h-4 text-purple-400" />
              <span>Configure GitHub Webhook</span>
              <ArrowRight className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Hexagon Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="cyber-card p-6 rounded-3xl space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-mono tracking-widest uppercase">DATABASE ENGINE</span>
            <div className="p-2.5 bg-blue-500/10 rounded-2xl border border-blue-500/20 text-blue-400">
              <Database className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold font-heading text-white">MongoDB</p>
          <p className="text-xs text-slate-400 font-mono">Atlas Cloud Persistence</p>
        </div>

        <div className="cyber-card p-6 rounded-3xl space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-mono tracking-widest uppercase">TOTAL AUDITS</span>
            <div className="p-2.5 bg-purple-500/10 rounded-2xl border border-purple-500/20 text-purple-400">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold font-heading text-white">{stats.totalScans}</p>
          <p className="text-xs text-slate-400 font-mono">Stored Audit History</p>
        </div>

        <div className="cyber-card p-6 rounded-3xl space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-mono tracking-widest uppercase">APPROVED BUILDS</span>
            <div className="p-2.5 bg-emerald-500/10 rounded-2xl border border-emerald-500/20 text-emerald-400">
              <CheckCircle className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold font-heading text-emerald-400">{stats.passedCount}</p>
          <p className="text-xs text-slate-400 font-mono">Safe to Deploy</p>
        </div>

        <div className="cyber-card p-6 rounded-3xl space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-mono tracking-widest uppercase">BLOCKED BUILDS</span>
            <div className="p-2.5 bg-rose-500/10 rounded-2xl border border-rose-500/20 text-rose-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold font-heading text-rose-400">{stats.criticalCount}</p>
          <p className="text-xs text-slate-400 font-mono">Deployment Blocked</p>
        </div>
      </div>

      {/* Live Engine Pipeline */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="cyber-card p-6 rounded-3xl space-y-3 border-l-4 border-l-cyan-400">
          <div className="flex items-center space-x-3 text-cyan-400">
            <Cpu className="w-5 h-5" />
            <h3 className="font-bold font-heading text-white text-base">1. SAST Static Engine</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Python AST syntax tree visitor searching for SQL injection, hardcoded credentials, command execution, and weak hashes.
          </p>
          <div className="pt-1 text-[11px] font-mono text-emerald-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>AST Visitor Ready</span>
          </div>
        </div>

        <div className="cyber-card p-6 rounded-3xl space-y-3 border-l-4 border-l-purple-400">
          <div className="flex items-center space-x-3 text-purple-400">
            <Zap className="w-5 h-5" />
            <h3 className="font-bold font-heading text-white text-base">2. DAST Sandbox</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Subprocess execution runner profiling RAM usage, CPU spikes, execution timeouts, and runtime exceptions.
          </p>
          <div className="pt-1 text-[11px] font-mono text-emerald-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Process Sandbox Ready</span>
          </div>
        </div>

        <div className="cyber-card p-6 rounded-3xl space-y-3 border-l-4 border-l-indigo-400">
          <div className="flex items-center space-x-3 text-indigo-400">
            <Sparkles className="w-5 h-5" />
            <h3 className="font-bold font-heading text-white text-base">3. LLM Governance AI</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Evaluates corporate policy guidelines using Groq Llama 3.3, generating structured JSON reviews with code fixes.
          </p>
          <div className="pt-1 text-[11px] font-mono text-emerald-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Policy Reviewer Ready</span>
          </div>
        </div>
      </div>

      {/* Audit History Timeline Table */}
      <div className="cyber-card rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold font-heading text-white">Recent Audit History Timeline</h3>
            <p className="text-xs text-slate-400 font-mono">Latest security audit runs stored in MongoDB Atlas</p>
          </div>
          <button
            onClick={() => setActiveTab('history')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-mono font-semibold flex items-center space-x-1"
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
              <thead className="text-slate-400 uppercase bg-slate-900/80 font-mono">
                <tr>
                  <th className="px-5 py-3.5">Scan ID</th>
                  <th className="px-5 py-3.5">Audit Target</th>
                  <th className="px-5 py-3.5">Verdict</th>
                  <th className="px-5 py-3.5">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {recentScans.map((scan) => {
                  const decision = scan.verdict?.decision || (scan.status === 'critical' || scan.can_deploy === false ? 'BLOCK' : 'APPROVE')
                  return (
                    <tr key={scan.scan_id || Math.random()} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-5 py-3.5 font-mono text-cyan-400 font-bold">{scan.scan_id?.slice(0, 8) || 'N/A'}</td>
                      <td className="px-5 py-3.5 text-slate-200 font-medium">{scan.file || scan.repository || scan.project_name || 'Uploaded Source Code'}</td>
                      <td className="px-5 py-3.5">
                        <span className={`px-2.5 py-1 rounded-full font-mono text-[10px] font-bold ${
                          decision === 'BLOCK' ? 'badge-block' : decision === 'WARN' ? 'badge-warn' : 'badge-approve'
                        }`}>
                          {decision}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-slate-400 font-mono">
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
