import React, { useState } from 'react'
import { FileCode, Github, Upload, Play, AlertTriangle, CheckCircle, ShieldAlert, Sparkles, Cpu, Zap, Code, ArrowRight, Check, RefreshCw, FileText } from 'lucide-react'
import axios from 'axios'

export default function Scanner() {
  const [scanType, setScanType] = useState('code') // 'code' or 'github'
  const [code, setCode] = useState('')
  const [githubUrl, setGithubUrl] = useState('')
  const [githubBranch, setGithubBranch] = useState('main')
  const [fileObj, setFileObj] = useState(null)
  
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)

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
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 cyber-card p-6 rounded-3xl">
        <div>
          <h2 className="text-xl font-extrabold text-white font-heading">Code Security Scanner</h2>
          <p className="text-xs text-slate-400">Scan source code files or full GitHub repositories for security vulnerabilities</p>
        </div>

        {/* Dual Mode Switcher */}
        <div className="flex p-1 bg-slate-900 rounded-2xl border border-slate-800 self-start sm:self-auto">
          <button
            onClick={() => setScanType('code')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              scanType === 'code'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold shadow-glow-cyan'
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
            <span>GitHub Repository</span>
          </button>
        </div>
      </div>

      {/* Main Input Workbench */}
      {scanType === 'code' ? (
        <div className="cyber-card p-6 rounded-3xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Code className="w-4 h-4 text-cyan-400" />
              <span className="font-bold text-white text-xs font-heading">Python Code Editor</span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleSampleCode}
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700 transition-all flex items-center space-x-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                <span>Load Sample Code</span>
              </button>
              <label className="px-3 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs font-mono border border-cyan-500/30 transition-all cursor-pointer flex items-center space-x-1.5">
                <Upload className="w-3.5 h-3.5" />
                <span>Upload File</span>
                <input type="file" accept=".py,.js,.java,.cpp,.ts" onChange={handleFileUpload} className="hidden" />
              </label>
            </div>
          </div>

          <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-[#070A14]">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              rows={12}
              className="w-full p-4 bg-transparent text-slate-200 font-mono text-xs leading-relaxed focus:outline-none resize-y"
              placeholder="Paste or upload your Python code here..."
            />
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleScanCode}
              disabled={scanning || (!code.trim() && !fileObj)}
              className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 text-slate-950 font-extrabold text-xs font-heading rounded-2xl shadow-glow-cyan transition-all disabled:opacity-40"
            >
              {scanning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Auditing Code...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Start Audit</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* GitHub URL Input Box */
        <div className="cyber-card p-6 rounded-3xl space-y-6">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-purple-500/10 text-purple-400 rounded-2xl border border-purple-500/20">
              <Github className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-sm font-heading">Audit GitHub Repository</h3>
              <p className="text-xs text-slate-400">Scan remote repository code files across all folders</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-1.5">
              <label className="text-[11px] font-mono text-slate-400">Repository URL</label>
              <input
                type="text"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/username/repository-name"
                className="w-full px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-2xl text-slate-200 text-xs font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[11px] font-mono text-slate-400">Branch</label>
              <input
                type="text"
                value={githubBranch}
                onChange={(e) => setGithubBranch(e.target.value)}
                placeholder="main"
                className="w-full px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-2xl text-slate-200 text-xs font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleScanGithub}
              disabled={scanning || !githubUrl.trim()}
              className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-extrabold text-xs font-heading rounded-2xl shadow-glow-purple transition-all disabled:opacity-40"
            >
              {scanning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Fetching Repository...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Audit Repository</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Audit Verdict & Findings */}
      {scanResult && (
        <div className="space-y-6">
          {(() => {
            const verdict = scanResult.verdict?.decision || (scanResult.can_deploy === false || scanResult.status === 'critical' ? 'BLOCK' : 'APPROVE')
            const isBlock = verdict === 'BLOCK'
            const isWarn = verdict === 'WARN'

            return (
              <div className={`p-6 rounded-3xl border ${
                isBlock ? 'bg-rose-950/30 border-rose-500/40' : isWarn ? 'bg-amber-950/30 border-amber-500/40' : 'bg-emerald-950/30 border-emerald-500/40'
              }`}>
                <div className="flex items-center space-x-4">
                  <div className={`p-3 rounded-2xl ${
                    isBlock ? 'bg-rose-500/20 text-rose-400' : isWarn ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    {isBlock ? <ShieldAlert className="w-6 h-6" /> : isWarn ? <AlertTriangle className="w-6 h-6" /> : <CheckCircle className="w-6 h-6" />}
                  </div>
                  <div>
                    <div className="flex items-center space-x-3">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                        isBlock ? 'badge-block' : isWarn ? 'badge-warn' : 'badge-approve'
                      }`}>
                        VERDICT: {verdict}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        Files Analyzed: {scanResult.files_analyzed || scanResult.summary?.files_analyzed || 1}
                      </span>
                    </div>
                    <h3 className="text-base font-extrabold text-white font-heading mt-1">
                      {scanResult.verdict?.reason || scanResult.message || 'Audit Complete'}
                    </h3>
                  </div>
                </div>
              </div>
            )
          })()}

          {/* Findings Cards */}
          <div className="cyber-card p-6 rounded-3xl space-y-4">
            <h3 className="text-sm font-bold text-white font-heading flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Vulnerability Findings</span>
            </h3>

            {(() => {
              const sastFindings = scanResult.engines?.sast?.findings || scanResult.sast_results?.findings || []
              const dastFindings = scanResult.engines?.dast?.findings || scanResult.dast_results?.findings || []
              const govFindings = scanResult.engines?.governance?.findings || scanResult.governance_results?.findings || []

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
                  <div className="p-6 text-center space-y-1">
                    <CheckCircle className="w-8 h-8 text-emerald-400 mx-auto" />
                    <h4 className="text-sm font-bold text-white">No Vulnerabilities Detected</h4>
                    <p className="text-xs text-slate-400 font-mono">Code passes OWASP security standards.</p>
                  </div>
                )
              }

              return (
                <div className="space-y-3">
                  {allFindings.map((finding, idx) => (
                    <div key={idx} className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2">
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                              finding.severity === 'CRITICAL' ? 'badge-block' : finding.severity === 'HIGH' ? 'badge-warn' : 'bg-blue-500/10 text-cyan-400 border border-blue-500/20'
                            }`}>
                              {finding.severity || 'MEDIUM'}
                            </span>
                            <span className="text-xs font-mono text-cyan-400 font-semibold">{finding.rule}</span>
                            {finding.line && <span className="text-[11px] text-slate-500 font-mono">Line {finding.line}</span>}
                          </div>
                          <p className="text-xs text-slate-300">{finding.message}</p>
                        </div>
                      </div>

                      {finding.oldCode && finding.newCode && (
                        <div className="p-3 rounded-xl bg-[#050811] border border-slate-800 space-y-1.5 font-mono text-xs">
                          <div className="flex items-center justify-between text-[11px] text-slate-500">
                            <span>SUGGESTED CODE FIX</span>
                            <button
                              onClick={() => applyAutoFix(finding.oldCode, finding.newCode)}
                              className="px-2 py-0.5 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-[10px] font-bold border border-emerald-500/30 transition-all flex items-center space-x-1"
                            >
                              <Check className="w-3 h-3" />
                              <span>Apply Fix</span>
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
