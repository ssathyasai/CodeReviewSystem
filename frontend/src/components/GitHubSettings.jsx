import React, { useState, useEffect } from 'react'
import { Github, Key, CheckCircle, AlertTriangle, ShieldCheck } from 'lucide-react'
import axios from 'axios'

export default function GitHubSettings() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchGitHubStatus()
  }, [])

  const fetchGitHubStatus = async () => {
    try {
      setLoading(true)
      const res = await axios.get('/github/status')
      setStatus(res.data)
    } catch (err) {
      console.error('Error fetching GitHub status:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white">GitHub Webhook Security Integration</h2>
        <p className="text-sm text-gray-400">Configure HMAC SHA-256 signatures for GitHub push webhooks</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Status Card */}
        <div className="glass-panel p-6 rounded-2xl space-y-6">
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            <span>Security Status</span>
          </h3>

          {loading ? (
            <p className="text-xs text-gray-500 py-6 text-center">Checking webhook security status...</p>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-xl bg-gray-950 border border-gray-800 text-xs">
                <span className="text-gray-300">Webhook Secret Configured (.env)</span>
                <span className={`px-2.5 py-1 rounded-full font-mono text-[10px] ${
                  status?.webhook_secret_set
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                }`}>
                  {status?.webhook_secret_set ? 'ENFORCED (HMAC SHA-256)' : 'NOT SET'}
                </span>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-gray-950 border border-gray-800 text-xs">
                <span className="text-gray-300">Git Binary Available</span>
                <span className={`px-2.5 py-1 rounded-full font-mono text-[10px] ${
                  status?.git_available
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {status?.git_available ? 'READY' : 'MISSING'}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-gray-950 border border-gray-800 space-y-2 text-xs font-mono">
                <p className="text-gray-400">WEBHOOK ENDPOINT URL:</p>
                <p className="text-blue-400 font-bold">http://your-server-domain.com/github/webhook</p>
              </div>
            </div>
          )}
        </div>

        {/* Setup Instructions */}
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <Github className="w-4 h-4 text-purple-400" />
            <span>GitHub Webhook Setup Guide</span>
          </h3>

          <ol className="space-y-3 text-xs text-gray-300 list-decimal list-inside leading-relaxed">
            <li className="p-2 rounded bg-gray-900/50">Go to your GitHub Repository &rarr; <span className="text-white font-medium">Settings &rarr; Webhooks</span>.</li>
            <li className="p-2 rounded bg-gray-900/50">Click <span className="text-white font-medium">Add Webhook</span>.</li>
            <li className="p-2 rounded bg-gray-900/50">Set <span className="text-white font-medium">Payload URL</span> to your FastAPI server URL + <code className="text-blue-400 font-mono">/github/webhook</code>.</li>
            <li className="p-2 rounded bg-gray-900/50">Set <span className="text-white font-medium">Content type</span> to <code className="text-purple-400 font-mono">application/json</code>.</li>
            <li className="p-2 rounded bg-gray-900/50">Set <span className="text-white font-medium">Secret</span> to match your <code className="text-emerald-400 font-mono">GITHUB_WEBHOOK_SECRET</code> in <code className="text-gray-400 font-mono">.env</code>.</li>
            <li className="p-2 rounded bg-gray-900/50">Select <span className="text-white font-medium">Just the push event</span> and save.</li>
          </ol>
        </div>

      </div>
    </div>
  )
}
