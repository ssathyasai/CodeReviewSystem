import React, { useState } from 'react'
import { Github, ShieldCheck, Copy, Check, Terminal, ExternalLink, Lock } from 'lucide-react'

export default function GitHubSettings() {
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [copiedSecret, setCopiedSecret] = useState(false)

  const webhookUrl = `${window.location.origin}/github-webhook`
  const secretKey = 'my_secret_key_123'

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

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-box p-6 rounded-3xl">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-2xl border border-indigo-500/20">
            <Github className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-white">GitHub Webhook & HMAC Signature Security</h2>
            <p className="text-xs text-slate-400">Automate code audits on every `git push` with SHA-256 HMAC verification</p>
          </div>
        </div>

        <div className="px-3.5 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 text-xs font-mono flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4" />
          <span>HMAC SHA-256 Enforced</span>
        </div>
      </div>

      {/* Grid Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Step-by-Step Guide */}
        <div className="lg:col-span-7 glass-box p-6 rounded-3xl space-y-6">
          <h3 className="text-base font-bold text-white flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>GitHub Webhook Setup Guide</span>
          </h3>

          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1.5">
              <div className="font-bold text-white flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-blue-600/30 text-cyan-400 flex items-center justify-center font-mono text-[10px] border border-cyan-500/30">1</span>
                <span>Navigate to Repository Settings</span>
              </div>
              <p className="text-slate-400 pl-7">Go to your GitHub repository &rarr; **Settings** &rarr; **Webhooks** &rarr; **Add webhook**.</p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1.5">
              <div className="font-bold text-white flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-blue-600/30 text-cyan-400 flex items-center justify-center font-mono text-[10px] border border-cyan-500/30">2</span>
                <span>Configure Payload URL & Content Type</span>
              </div>
              <p className="text-slate-400 pl-7">Set Content type to `application/json` and paste your webhook endpoint URL.</p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1.5">
              <div className="font-bold text-white flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-blue-600/30 text-cyan-400 flex items-center justify-center font-mono text-[10px] border border-cyan-500/30">3</span>
                <span>Enter Secret Key for Signature Verification</span>
              </div>
              <p className="text-slate-400 pl-7">Enter your secret key in the Secret field to sign payloads with `X-Hub-Signature-256`.</p>
            </div>
          </div>
        </div>

        {/* Copyable Keys Section */}
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
              <label className="text-xs font-mono text-slate-400">Webhook Secret (`GITHUB_WEBHOOK_SECRET`)</label>
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
    </div>
  )
}
