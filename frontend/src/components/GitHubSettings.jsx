import React, { useState, useEffect } from 'react'
import {
  Github,
  ShieldCheck,
  Copy,
  Check,
  Terminal,
  Lock,
  GitPullRequest,
  GitCommit,
  GitBranch,
  Search,
  Filter,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
  RefreshCw,
  Zap,
  Play,
  ArrowRight,
  ChevronRight,
  FileCode,
  User,
  Clock,
  Sparkles,
  ExternalLink,
  Code
} from 'lucide-react'
import axios from 'axios'

export default function GitHubSettings({ currentUser }) {
  const [activeSubTab, setActiveSubTab] = useState('tracker') // 'tracker', 'audit', 'credentials'
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedScan, setSelectedScan] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [copiedSecret, setCopiedSecret] = useState(false)

  // Manual Scan state
  const [repoUrlInput, setRepoUrlInput] = useState('')
  const [branchInput, setBranchInput] = useState('main')
  const [isScanningRepo, setIsScanningRepo] = useState(false)

  // Test Push Simulation state
  const [isSimulatingPush, setIsSimulatingPush] = useState(false)
  const [simulationNotice, setSimulationNotice] = useState(null)

  const webhookUrl = `${window.location.origin}/github/webhook`
  const secretKey = 'my_secret_key_123'

  useEffect(() => {
    fetchWebhookScans()

    // Setup WebSocket listener for live push events
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    let socket = null

    try {
      socket = new WebSocket(wsUrl)
      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'github_analysis_complete' || msg.type === 'scan_complete') {
            fetchWebhookScans()
          }
        } catch (e) {
          console.error('WebSocket parse error:', e)
        }
      }
    } catch (e) {
      console.error('WebSocket connection error:', e)
    }

    return () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close()
      }
    }
  }, [])

  const fetchWebhookScans = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/scans?limit=100')
      const allScans = res.data.scans || []
      // Filter scans that originate from GitHub webhooks or GitHub repo scans
      const githubScans = allScans.filter(
        (s) => s.scan_type === 'github_webhook' || s.is_webhook || s.repository || s.metadata?.repository
      )
      setScans(githubScans.length > 0 ? githubScans : allScans)
    } catch (err) {
      console.error('Failed to fetch webhook scans:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleManualRepoScan = async (e) => {
    e.preventDefault()
    if (!repoUrlInput.trim()) return

    setIsScanningRepo(true)
    try {
      const res = await axios.post('/github/scan-repo', {
        repo_url: repoUrlInput.trim(),
        branch: branchInput.trim() || 'main',
        username: currentUser?.username
      })
      fetchWebhookScans()
      setSelectedScan(res.data)
      setActiveSubTab('tracker')
    } catch (err) {
      console.error('Repo scan failed:', err)
      alert(err.response?.data?.error || 'Failed to scan repository')
    } finally {
      setIsScanningRepo(false)
    }
  }

  const handleSimulatePush = async () => {
    setIsSimulatingPush(true)
    setSimulationNotice(null)
    try {
      const res = await axios.post('/github/simulate-push', {
        repo_name: 'ssathyasai/CodeReviewSystem',
        branch: 'main',
        pusher: currentUser?.username || 'alex-dev'
      })
      setSimulationNotice('✅ Simulated push event received & code review generated!')
      fetchWebhookScans()
      setSelectedScan(res.data)
      setActiveSubTab('tracker')
      setTimeout(() => setSimulationNotice(null), 5000)
    } catch (err) {
      console.error('Push simulation failed:', err)
    } finally {
      setIsSimulatingPush(false)
    }
  }

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text)
    if (type === 'url') {
      setCopiedUrl(true)
      setTimeout(() => setCopiedUrl(false), 2000)
    } else {
      setCopiedSecret(true)
      setTimeout(() => setCopiedSecret(false), 2000)
    }
  }

  // Filter scans
  const filteredScans = scans.filter((scan) => {
    const repo = scan.repository || scan.metadata?.repository || scan.project_name || scan.file || ''
    const pusher = scan.metadata?.pusher || ''
    const matchesQuery = repo.toLowerCase().includes(searchQuery.toLowerCase()) || pusher.toLowerCase().includes(searchQuery.toLowerCase())

    const verdict = scan.verdict?.decision || (scan.can_deploy === false ? 'BLOCK' : 'APPROVE')
    if (statusFilter === 'ALL') return matchesQuery
    return matchesQuery && verdict === statusFilter
  })

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-box p-6 rounded-3xl">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-2xl border border-indigo-500/20 glow-indigo">
            <Github className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-white">Webhook Projects & Pushed Code Review</h2>
            <p className="text-xs text-slate-400">Track repository push events, automate code reviews, and inspect security findings</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleSimulatePush}
            disabled={isSimulatingPush}
            className="px-4 py-2 rounded-2xl bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 text-xs font-bold font-mono transition-all flex items-center space-x-2 shrink-0"
          >
            <Play className={`w-3.5 h-3.5 ${isSimulatingPush ? 'animate-spin' : 'fill-current'}`} />
            <span>{isSimulatingPush ? 'Simulating Push...' : 'Test Webhook Push'}</span>
          </button>

          <div className="px-3.5 py-2 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 text-xs font-mono flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>HMAC SHA-256 Active</span>
          </div>
        </div>
      </div>

      {simulationNotice && (
        <div className="p-4 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-mono flex items-center justify-between animate-fade-in">
          <span>{simulationNotice}</span>
          <button onClick={() => setSimulationNotice(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Interactive Workflow Visual Guide */}
      <div className="glass-box p-6 rounded-3xl space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest font-mono flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span>How To Use Your Webhook Project</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
            <div className="flex items-center justify-between">
              <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 font-extrabold text-xs flex items-center justify-center border border-cyan-500/30">1</span>
              <GitCommit className="w-4 h-4 text-slate-500" />
            </div>
            <h4 className="font-bold text-white">1. Developer Pushes Code</h4>
            <p className="text-[11px] text-slate-400 font-sans">Run <code className="text-cyan-300 bg-slate-950 px-1 py-0.5 rounded">git push origin main</code> in your connected repository.</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
            <div className="flex items-center justify-between">
              <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 font-extrabold text-xs flex items-center justify-center border border-cyan-500/30">2</span>
              <Lock className="w-4 h-4 text-slate-500" />
            </div>
            <h4 className="font-bold text-white">2. HMAC Webhook Signal</h4>
            <p className="text-[11px] text-slate-400 font-sans">GitHub sends an HTTP push payload verified with SHA-256 HMAC signature.</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
            <div className="flex items-center justify-between">
              <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 font-extrabold text-xs flex items-center justify-center border border-cyan-500/30">3</span>
              <Zap className="w-4 h-4 text-slate-500" />
            </div>
            <h4 className="font-bold text-white">3. Automated Code Audit</h4>
            <p className="text-[11px] text-slate-400 font-sans">Semgrep SAST & Llama 3.3 AI audit changed Python code line-by-line.</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
            <div className="flex items-center justify-between">
              <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 font-extrabold text-xs flex items-center justify-center border border-cyan-500/30">4</span>
              <ShieldCheck className="w-4 h-4 text-slate-500" />
            </div>
            <h4 className="font-bold text-white">4. Track & Review Code</h4>
            <p className="text-[11px] text-slate-400 font-sans">Inspect pushed code reviews, security findings & deployment verdicts below.</p>
          </div>
        </div>
      </div>

      {/* Sub Tab Navigation */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveSubTab('tracker')}
          className={`px-4 py-2 rounded-2xl font-extrabold text-xs transition-all flex items-center space-x-2 ${
            activeSubTab === 'tracker'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <GitPullRequest className="w-4 h-4" />
          <span>Pushed Code Reviews ({filteredScans.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab('audit')}
          className={`px-4 py-2 rounded-2xl font-extrabold text-xs transition-all flex items-center space-x-2 ${
            activeSubTab === 'audit'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Search className="w-4 h-4" />
          <span>Audit Repo URL / Test Push</span>
        </button>

        <button
          onClick={() => setActiveSubTab('credentials')}
          className={`px-4 py-2 rounded-2xl font-extrabold text-xs transition-all flex items-center space-x-2 ${
            activeSubTab === 'credentials'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Lock className="w-4 h-4" />
          <span>Webhook Setup & HMAC Credentials</span>
        </button>
      </div>

      {/* ================= TAB 1: Pushed Code Tracker & Reviews ================= */}
      {activeSubTab === 'tracker' && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 glass-box p-4 rounded-2xl">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search pushed repository, pusher, or commit..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-900/90 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
              />
            </div>

            <div className="flex items-center space-x-2 shrink-0">
              <span className="text-xs text-slate-400 font-mono flex items-center space-x-1">
                <Filter className="w-3.5 h-3.5" />
                <span>Verdict:</span>
              </span>
              {['ALL', 'APPROVE', 'WARN', 'BLOCK'].map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`px-3 py-1 rounded-xl text-xs font-mono font-bold transition-all ${
                    statusFilter === status
                      ? status === 'APPROVE'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : status === 'BLOCK'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  {status}
                </button>
              ))}

              <button
                onClick={fetchWebhookScans}
                className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded-xl border border-slate-800 transition-all"
                title="Refresh scan feed"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Webhook Projects / Push Event List */}
          {filteredScans.length === 0 ? (
            <div className="glass-box p-12 text-center rounded-3xl space-y-3">
              <div className="p-4 bg-slate-900/80 rounded-full w-14 h-14 mx-auto flex items-center justify-center text-slate-500 border border-slate-800">
                <GitPullRequest className="w-7 h-7" />
              </div>
              <h4 className="text-base font-bold text-white">No Webhook Push Reviews Yet</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No code has been pushed to your webhook endpoint yet. Push code to your GitHub repo or click <strong>Test Webhook Push</strong> above to generate a sample code review report.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {filteredScans.map((scan, idx) => {
                const repoName = scan.repository || scan.metadata?.repository || scan.project_name || scan.file || 'GitHub Repository'
                const branch = scan.branch || scan.metadata?.branch || 'main'
                const pusher = scan.metadata?.pusher || scan.username || 'git-pusher'
                const timestamp = scan.timestamp ? new Date(scan.timestamp).toLocaleString() : 'Just now'
                const totalIssues = scan.summary?.total_issues ?? (scan.files?.reduce((acc, f) => acc + (f.findings_count || 0), 0) || 0)
                const criticalCount = scan.summary?.critical_issues || scan.critical_count || 0
                const highCount = scan.summary?.high_issues || 0

                const canDeploy = scan.can_deploy !== false && criticalCount === 0
                const verdictLabel = scan.verdict?.decision || (canDeploy ? 'APPROVE' : 'BLOCK')

                return (
                  <div
                    key={scan.scan_id || idx}
                    className="glass-box p-5 rounded-2xl hover:border-slate-700 transition-all space-y-4"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                      <div className="flex items-center space-x-3">
                        <div className={`p-3 rounded-2xl border ${
                          verdictLabel === 'APPROVE'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        }`}>
                          <Github className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h4 className="font-extrabold text-sm text-white font-heading">{repoName}</h4>
                            <span className="px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-[10px] font-mono text-cyan-400 flex items-center space-x-1">
                              <GitBranch className="w-3 h-3" />
                              <span>{branch}</span>
                            </span>
                          </div>
                          <div className="flex items-center space-x-3 text-[11px] text-slate-400 font-mono mt-1">
                            <span className="flex items-center space-x-1">
                              <User className="w-3 h-3 text-slate-500" />
                              <span>Pushed by: <strong className="text-slate-300">{pusher}</strong></span>
                            </span>
                            <span>&bull;</span>
                            <span className="flex items-center space-x-1">
                              <Clock className="w-3 h-3 text-slate-500" />
                              <span>{timestamp}</span>
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-3">
                        <span className={`px-3 py-1 rounded-full text-xs font-mono font-bold flex items-center space-x-1 border ${
                          verdictLabel === 'APPROVE'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                        }`}>
                          {verdictLabel === 'APPROVE' ? <CheckCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                          <span>Verdict: {verdictLabel}</span>
                        </span>

                        <button
                          onClick={() => setSelectedScan(scan)}
                          className="px-3.5 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-xs font-semibold font-mono transition-all flex items-center space-x-1.5"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Review Pushed Code</span>
                        </button>
                      </div>
                    </div>

                    {/* Summary metrics strip */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/60 text-xs font-mono">
                      <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between">
                        <span className="text-slate-400">Total Findings:</span>
                        <span className="font-bold text-white">{totalIssues}</span>
                      </div>
                      <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between">
                        <span className="text-slate-400">Critical Issues:</span>
                        <span className={`font-bold ${criticalCount > 0 ? 'text-rose-400' : 'text-slate-400'}`}>{criticalCount}</span>
                      </div>
                      <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between">
                        <span className="text-slate-400">High Severity:</span>
                        <span className={`font-bold ${highCount > 0 ? 'text-amber-400' : 'text-slate-400'}`}>{highCount}</span>
                      </div>
                      <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between">
                        <span className="text-slate-400">Deploy Safe:</span>
                        <span className={`font-bold ${canDeploy ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {canDeploy ? 'YES' : 'NO'}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 2: Manual Repo Audit & Push Test ================= */}
      {activeSubTab === 'audit' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 glass-box p-6 rounded-3xl space-y-6">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Github className="w-4 h-4 text-cyan-400" />
              <span>Audit Any GitHub Repository Link</span>
            </h3>
            <p className="text-xs text-slate-400">
              Enter any public or private GitHub repository URL below to trigger an immediate code review and track it as a project.
            </p>

            <form onSubmit={handleManualRepoScan} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-slate-400">GitHub Repository URL</label>
                <input
                  type="url"
                  required
                  placeholder="https://github.com/username/repository"
                  value={repoUrlInput}
                  onChange={(e) => setRepoUrlInput(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-mono text-slate-400">Branch Name</label>
                <input
                  type="text"
                  placeholder="main"
                  value={branchInput}
                  onChange={(e) => setBranchInput(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>

              <button
                type="submit"
                disabled={isScanningRepo}
                className="w-full py-3 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-extrabold text-xs font-heading flex items-center justify-center space-x-2 shadow-glow-cyan transition-all"
              >
                {isScanningRepo ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Cloning & Auditing Repository...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 fill-current" />
                    <span>Run Full Repository Review</span>
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="lg:col-span-5 glass-box p-6 rounded-3xl space-y-6 flex flex-col justify-between">
            <div className="space-y-3">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <Play className="w-4 h-4 text-purple-400" />
                <span>Simulate Webhook Push Event</span>
              </h3>
              <p className="text-xs text-slate-400">
                Want to test pushed code review without opening your terminal? Click below to send a sample webhook push payload directly to the system.
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2 text-xs font-mono text-slate-400">
              <div className="flex items-center space-x-2 text-cyan-400 font-bold">
                <Terminal className="w-4 h-4" />
                <span>Simulated Payload Info:</span>
              </div>
              <p>&bull; Repo: <code className="text-slate-200">ssathyasai/CodeReviewSystem</code></p>
              <p>&bull; Event: <code className="text-slate-200">push (refs/heads/main)</code></p>
              <p>&bull; Changed files: <code className="text-slate-200">backend/payment_gateway.py</code></p>
            </div>

            <button
              onClick={handleSimulatePush}
              disabled={isSimulatingPush}
              className="w-full py-3 rounded-2xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/40 font-extrabold text-xs font-mono flex items-center justify-center space-x-2 transition-all"
            >
              <Play className={`w-4 h-4 ${isSimulatingPush ? 'animate-spin' : ''}`} />
              <span>{isSimulatingPush ? 'Generating Review...' : 'Trigger Test Push Event'}</span>
            </button>
          </div>
        </div>
      )}

      {/* ================= TAB 3: Webhook Setup & Credentials ================= */}
      {activeSubTab === 'credentials' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Setup Guide */}
          <div className="lg:col-span-7 glass-box p-6 rounded-3xl space-y-6">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span>GitHub Webhook Integration Steps</span>
            </h3>

            <div className="space-y-4 text-xs">
              <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1.5">
                <div className="font-bold text-white flex items-center space-x-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600/30 text-cyan-400 flex items-center justify-center font-mono text-[10px] border border-cyan-500/30">1</span>
                  <span>Open GitHub Repository Webhook Settings</span>
                </div>
                <p className="text-slate-400 pl-7">In your GitHub repository, navigate to <strong>Settings</strong> &rarr; <strong>Webhooks</strong> &rarr; <strong>Add webhook</strong>.</p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1.5">
                <div className="font-bold text-white flex items-center space-x-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600/30 text-cyan-400 flex items-center justify-center font-mono text-[10px] border border-cyan-500/30">2</span>
                  <span>Paste Payload URL & Content Type</span>
                </div>
                <p className="text-slate-400 pl-7">Set Payload URL to the URL on the right and set Content type to <code className="text-cyan-300">application/json</code>.</p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1.5">
                <div className="font-bold text-white flex items-center space-x-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600/30 text-cyan-400 flex items-center justify-center font-mono text-[10px] border border-cyan-500/30">3</span>
                  <span>Set HMAC Secret & Select Push Events</span>
                </div>
                <p className="text-slate-400 pl-7">Paste your secret key into the Secret field and select "Just the push event".</p>
              </div>
            </div>
          </div>

          {/* Credentials */}
          <div className="lg:col-span-5 glass-box p-6 rounded-3xl space-y-6">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Lock className="w-4 h-4 text-purple-400" />
              <span>Webhook Credentials</span>
            </h3>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-slate-400">Payload URL</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    readOnly
                    value={webhookUrl}
                    className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-cyan-300 font-mono text-xs focus:outline-none"
                  />
                  <button
                    onClick={() => copyToClipboard(webhookUrl, 'url')}
                    className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 transition-all shrink-0"
                  >
                    {copiedUrl ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-mono text-slate-400">Webhook Secret Key (`GITHUB_WEBHOOK_SECRET`)</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    readOnly
                    value={secretKey}
                    className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-purple-300 font-mono text-xs focus:outline-none"
                  />
                  <button
                    onClick={() => copyToClipboard(secretKey, 'secret')}
                    className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 transition-all shrink-0"
                  >
                    {copiedSecret ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= DETAILED PUSHED CODE REVIEW MODAL ================= */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto">
          <div className="glass-box max-w-4xl w-full rounded-3xl p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto relative border border-slate-700 shadow-2xl">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[11px] font-mono font-bold">
                    Pushed Code Review Report
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    ID: {selectedScan.scan_id?.substring(0, 8)}
                  </span>
                </div>
                <h3 className="text-xl font-extrabold text-white font-heading">
                  {selectedScan.repository || selectedScan.metadata?.repository || selectedScan.project_name || selectedScan.file}
                </h3>
              </div>

              <button
                onClick={() => setSelectedScan(null)}
                className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-all"
              >
                ✕
              </button>
            </div>

            {/* Verdict Status Banner */}
            <div className={`p-4 rounded-2xl border flex items-center justify-between ${
              selectedScan.can_deploy !== false
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
            }`}>
              <div className="flex items-center space-x-3">
                {selectedScan.can_deploy !== false ? <CheckCircle className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
                <div>
                  <h4 className="font-bold text-sm">
                    Verdict: {selectedScan.verdict?.decision || (selectedScan.can_deploy !== false ? 'APPROVED' : 'BLOCKED')}
                  </h4>
                  <p className="text-xs opacity-90">
                    {selectedScan.message || selectedScan.verdict?.reason || 'Push security audit evaluation complete.'}
                  </p>
                </div>
              </div>
            </div>

            {/* Changed Files Breakdown */}
            <div className="space-y-4">
              <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-widest flex items-center space-x-2">
                <FileCode className="w-4 h-4 text-cyan-400" />
                <span>Audited Python Code Files ({selectedScan.files?.length || 0})</span>
              </h4>

              {(!selectedScan.files || selectedScan.files.length === 0) ? (
                <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400">
                  No specific python file vulnerabilities found. Overall project status is clean.
                </div>
              ) : (
                <div className="space-y-4">
                  {selectedScan.files.map((fileObj, idx) => {
                    const filePath = fileObj.path || fileObj.filename || `file_${idx}`
                    const engines = fileObj.engines || {}

                    // Flatten findings from engines
                    const findings = []
                    if (engines.sast?.findings) findings.push(...engines.sast.findings.map(f => ({ ...f, source: 'SAST Semgrep' })))
                    if (engines.governance?.findings) findings.push(...engines.governance.findings.map(f => ({ ...f, source: 'AI Governance' })))
                    if (engines.dast?.findings) findings.push(...engines.dast.findings.map(f => ({ ...f, source: 'DAST Engine' })))

                    return (
                      <div key={idx} className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                        <div className="flex items-center justify-between font-mono text-xs">
                          <span className="font-bold text-cyan-300 flex items-center space-x-2">
                            <Code className="w-4 h-4 text-cyan-400" />
                            <span>{filePath}</span>
                          </span>
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                            {findings.length} issue(s)
                          </span>
                        </div>

                        {findings.length === 0 ? (
                          <p className="text-xs text-emerald-400 font-mono">✅ No security or compliance issues detected in this file.</p>
                        ) : (
                          <div className="space-y-2 pt-2 border-t border-slate-800/80">
                            {findings.map((f, fIdx) => (
                              <div key={fIdx} className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-xs space-y-1.5">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2 font-mono">
                                    <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[10px] font-bold border border-rose-500/30">
                                      {f.severity || 'HIGH'}
                                    </span>
                                    <span className="text-slate-400">Line {f.line || '1'}</span>
                                    <span className="text-purple-400 font-bold">&bull; {f.source}</span>
                                  </div>
                                </div>
                                <p className="text-slate-200">{f.issue || f.description || 'Vulnerability detected'}</p>
                                {f.recommendation && (
                                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[11px] text-cyan-300 space-y-1">
                                    <div className="text-slate-400 text-[10px] font-bold uppercase">AI Remediation Fix:</div>
                                    <p>{f.recommendation}</p>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-800">
              <button
                onClick={() => setSelectedScan(null)}
                className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition-all"
              >
                Close Review Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
