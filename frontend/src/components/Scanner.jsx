import React, { useState } from 'react'
import { FileCode, Github, Upload, Play, AlertTriangle, CheckCircle, ShieldAlert, Sparkles, Cpu, Zap, Code, ArrowRight, Check, RefreshCw, FileText } from 'lucide-react'
import axios from 'axios'

export default function Scanner() {
  const [scanType, setScanType] = useState('code') // 'code' or 'github'
  const [code, setCode] = useState(`import os
import sqlite3

# Vulnerable Code Sample
DATABASE_PASSWORD = "super_secret_123"
discount_rate = 0.25

def get_user(user_input):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # SQL Injection Risk
    cursor.execute(f"SELECT * FROM users WHERE username = '{user_input}'")
    return cursor.fetchall()
`)
  const [githubUrl, setGithubUrl] = useState('')
  const [githubBranch, setGithubBranch] = useState('main')
  const [fileObj, setFileObj] = useState(null)
  
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [activeEngineTab, setActiveEngineTab] = useState('all')

  const handleSampleCode = () => {
    setCode(`import os
import sqlite3

# Sample Financial Application
API_KEY = "sk_live_secret_998877"
price_discount = 0.15

def execute_user_query(query_param):
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    # SQL Injection Vulnerability
    cursor.execute(f"SELECT * FROM accounts WHERE id = {query_param}")
    return cursor.fetchall()
`)
  }

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setFileObj(file)
    const reader = new FileReader()
    reader.onload = (event) => setCode(event.target.result)
    reader.readAsText(file)
  }

  const handleScanCode = async () => {
    if (!code.trim() && !fileObj) return
    setScanning(true)
    setScanResult(null)

    try {
      const formData = new FormData()
      if (fileObj) {
        formData.append('file', fileObj)
      } else {
        const blob = new Blob([code], { type: 'text/plain' })
        formData.append('file', blob, 'source_code.py')
      }

      const res = await axios.post('/scan', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setScanResult(res.data)
    } catch (err) {
      console.error('Scan failed:', err)
      alert('Code scan failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setScanning(false)
    }
  }

  const handleScanGithub = async () => {
    if (!githubUrl.trim()) return
    setScanning(true)
    setScanResult(null)

    try {
      const res = await axios.post('/github/scan-repo', {
        repo_url: githubUrl.trim(),
        branch: githubBranch.trim() || 'main'
      })
      setScanResult(res.data)
    } catch (err) {
      console.error('GitHub scan failed:', err)
      alert('GitHub repo scan failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setScanning(false)
    }
  }

  const applyAutoFix = (oldCode, newCode) => {
    if (!oldCode || !newCode) return
    setCode(prev => prev.replace(oldCode, newCode))
  }

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-box p-6 rounded-3xl">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-cyan-400 text-xs font-mono mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>SAST + DAST + LLM Code Security Audit</span>
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">Code Security & Governance Scanner</h2>
          <p className="text-xs text-slate-400">Analyze source files or entire GitHub repositories for OWASP Top 10 vulnerabilities</p>
        </div>

        {/* Dual Mode Switcher Pill */}
        <div className="flex p-1.5 bg-slate-900/90 rounded-2xl border border-slate-800 self-start md:self-auto">
          <button
            onClick={() => setScanType('code')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              scanType === 'code'
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-glow-blue'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="w-4 h-4" />
            <span>Source Code File</span>
          </button>
          <button
            onClick={() => setScanType('github')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              scanType === 'github'
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-glow-purple'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Github className="w-4 h-4" />
            <span>GitHub Repo URL</span>
          </button>
        </div>
      </div>

      {/* Main Scanner Section */}
      {scanType === 'code' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Code Input Box */}
          <div className="lg:col-span-12 glass-box p-6 rounded-3xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Code className="w-5 h-5 text-cyan-400" />
                <span className="font-bold text-white text-sm">Python Source Code Editor</span>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleSampleCode}
                  className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700 transition-all flex items-center space-x-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Load Sample Code</span>
                </button>
                <label className="px-3 py-1.5 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 text-cyan-300 text-xs font-mono border border-cyan-500/30 transition-all cursor-pointer flex items-center space-x-1.5">
                  <Upload className="w-3.5 h-3.5" />
                  <span>Upload File</span>
                  <input type="file" accept=".py,.js,.java,.cpp,.ts" onChange={handleFileUpload} className="hidden" />
                </label>
              </div>
            </div>

            <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-[#090D16]">
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                rows={12}
                className="w-full p-4 bg-transparent text-slate-200 font-mono text-xs leading-relaxed focus:outline-none resize-y"
                placeholder="Paste your source code here..."
              />
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleScanCode}
                disabled={scanning}
                className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm rounded-2xl shadow-glow-blue transition-all disabled:opacity-50"
              >
                {scanning ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Running Security Audit Engines...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Audit Source Code</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* GitHub URL Input Box */
        <div className="glass-box p-8 rounded-3xl space-y-6">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-purple-500/10 text-purple-400 rounded-2xl border border-purple-500/20">
              <Github className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Audit Complete GitHub Repository</h3>
              <p className="text-xs text-slate-400">Downloads repository archive and analyzes all Python files across subfolders</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-1.5">
              <label className="text-xs font-mono text-slate-400">GitHub Repository URL</label>
              <input
                type="text"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/username/repository-name"
                className="w-full px-4 py-3 bg-slate-900/90 border border-slate-800 rounded-2xl text-slate-200 text-xs font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-slate-400">Branch Name</label>
              <input
                type="text"
                value={githubBranch}
                onChange={(e) => setGithubBranch(e.target.value)}
                placeholder="main"
                className="w-full px-4 py-3 bg-slate-900/90 border border-slate-800 rounded-2xl text-slate-200 text-xs font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleScanGithub}
              disabled={scanning}
              className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-sm rounded-2xl shadow-glow-purple transition-all disabled:opacity-50"
            >
              {scanning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Fetching & Scanning Repository...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Audit GitHub Repository</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Audit Results Section */}
      {scanResult && (
        <div className="space-y-6 animate-fadeIn">
          {/* Security Verdict Banner */}
          {(() => {
            const verdict = scanResult.verdict?.decision || (scanResult.can_deploy === false || scanResult.status === 'critical' ? 'BLOCK' : 'APPROVE')
            const isBlock = verdict === 'BLOCK'
            const isWarn = verdict === 'WARN'

            return (
              <div className={`p-8 rounded-3xl border ${
                isBlock ? 'bg-rose-950/40 border-rose-500/40' : isWarn ? 'bg-amber-950/40 border-amber-500/40' : 'bg-emerald-950/40 border-emerald-500/40'
              }`}>
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div className="flex items-center space-x-4">
                    <div className={`p-4 rounded-2xl ${
                      isBlock ? 'bg-rose-500/20 text-rose-400' : isWarn ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'
                    }`}>
                      {isBlock ? <ShieldAlert className="w-8 h-8" /> : isWarn ? <AlertTriangle className="w-8 h-8" /> : <CheckCircle className="w-8 h-8" />}
                    </div>
                    <div>
                      <div className="flex items-center space-x-3">
                        <span className={`px-3 py-1 rounded-full text-xs font-mono font-bold tracking-wider ${
                          isBlock ? 'badge-critical-glow' : isWarn ? 'badge-warning-glow' : 'badge-success-glow'
                        }`}>
                          VERDICT: {verdict}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">
                          Files Analyzed: {scanResult.files_analyzed || scanResult.summary?.files_analyzed || 1}
                        </span>
                      </div>
                      <h3 className="text-xl font-extrabold text-white mt-1">
                        {scanResult.verdict?.reason || scanResult.message || 'Security Audit Completed'}
                      </h3>
                    </div>
                  </div>
                </div>
              </div>
            )
          })()}

          {/* Engine Accordion Findings */}
          <div className="glass-box p-6 rounded-3xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Multi-Engine Findings Breakdown</span>
              </h3>
            </div>

            {/* Findings List */}
            {(() => {
              const sastFindings = scanResult.engines?.sast?.findings || scanResult.sast_results?.findings || []
              const dastFindings = scanResult.engines?.dast?.findings || scanResult.dast_results?.findings || []
              const govFindings = scanResult.engines?.governance?.findings || scanResult.governance_results?.findings || []

              // If scanning GitHub repo, aggregate findings from files
              let repoFindings = []
              if (scanResult.files && Array.isArray(scanResult.files)) {
                scanResult.files.forEach(f => {
                  if (f.engines) {
                    repoFindings.push(...(f.engines.sast?.findings || []))
                    repoFindings.push(...(f.engines.dast?.findings || []))
                    repoFindings.push(...(f.engines.governance?.findings || []))
                  }
                })
              }

              const allFindings = [...sastFindings, ...dastFindings, ...govFindings, ...repoFindings]

              if (allFindings.length === 0) {
                return (
                  <div className="p-8 text-center space-y-2">
                    <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto" />
                    <h4 className="text-base font-bold text-white">Zero Vulnerabilities Detected!</h4>
                    <p className="text-xs text-slate-400 font-mono">Code complies with OWASP Top 10 security standards.</p>
                  </div>
                )
              }

              return (
                <div className="space-y-4">
                  {allFindings.map((finding, idx) => (
                    <div key={idx} className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                              finding.severity === 'CRITICAL' ? 'badge-critical-glow' : finding.severity === 'HIGH' ? 'badge-warning-glow' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            }`}>
                              {finding.severity || 'MEDIUM'}
                            </span>
                            <span className="text-xs font-mono text-cyan-400 font-semibold">{finding.rule}</span>
                            {finding.line && <span className="text-[11px] text-slate-500 font-mono">Line {finding.line}</span>}
                          </div>
                          <p className="text-xs text-slate-300">{finding.message}</p>
                        </div>
                      </div>

                      {/* Code Diff Box if Auto-Fix available */}
                      {finding.oldCode && finding.newCode && (
                        <div className="p-4 rounded-xl bg-[#070A11] border border-slate-800/80 space-y-2 font-mono text-xs">
                          <div className="flex items-center justify-between text-[11px] text-slate-500">
                            <span>RECOMMENDED CODE FIX</span>
                            <button
                              onClick={() => applyAutoFix(finding.oldCode, finding.newCode)}
                              className="px-2.5 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-[10px] font-bold border border-emerald-500/30 transition-all flex items-center space-x-1"
                            >
                              <Check className="w-3 h-3" />
                              <span>Apply Auto-Fix</span>
                            </button>
                          </div>
                          <div className="text-rose-400 bg-rose-950/30 p-2 rounded border border-rose-500/20 overflow-x-auto">
                            - {finding.oldCode}
                          </div>
                          <div className="text-emerald-400 bg-emerald-950/30 p-2 rounded border border-emerald-500/20 overflow-x-auto">
                            + {finding.newCode}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>
        </div>
      )}
    </div>
  )
}
