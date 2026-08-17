import React, { useState } from 'react'
import { Upload, FileCode, CheckCircle, AlertTriangle, ShieldAlert, Cpu, Zap, Sparkles, Check, CornerDownRight, Github, Link } from 'lucide-react'
import axios from 'axios'

export default function Scanner() {
  const [scanMode, setScanMode] = useState('file') // 'file' or 'github'
  const [file, setFile] = useState(null)
  const [codeContent, setCodeContent] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [error, setError] = useState(null)
  const [appliedFixes, setAppliedFixes] = useState({})

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      const reader = new FileReader()
      reader.onload = (event) => {
        setCodeContent(event.target.result)
      }
      reader.readAsText(selectedFile)
    }
  }

  const handleRunScan = async () => {
    if (scanMode === 'github') {
      if (!repoUrl) {
        setError('Please enter a valid GitHub repository URL.')
        return
      }
      try {
        setScanning(true)
        setError(null)
        setScanResult(null)

        const res = await axios.post('/github/scan-repo', {
          repo_url: repoUrl,
          branch: branch || 'main'
        })
        setScanResult(res.data)
      } catch (err) {
        console.error('GitHub scan error:', err)
        setError(err.response?.data?.error || 'GitHub repository scan failed. Ensure Git is installed.')
      } finally {
        setScanning(false)
      }
      return
    }

    if (!file && !codeContent) {
      setError('Please select a file or enter code to scan.')
      return
    }

    try {
      setScanning(true)
      setError(null)
      setScanResult(null)

      let uploadFile = file
      if (!uploadFile) {
        const blob = new Blob([codeContent], { type: 'text/plain' })
        uploadFile = new File([blob], 'submitted_code.py', { type: 'text/plain' })
      }

      const formData = new FormData()
      formData.append('file', uploadFile)

      const res = await axios.post('/scan', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      setScanResult(res.data)
    } catch (err) {
      console.error('Scan error:', err)
      setError(err.response?.data?.error || 'Scan failed. Please verify backend service is running.')
    } finally {
      setScanning(false)
    }
  }

  const handleApplyFix = async (finding, index) => {
    if (!finding.newCode || !file) return
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('line', finding.line || 1)
      formData.append('new_code', finding.newCode)

      const res = await axios.post('/apply-fix', formData)
      if (res.data.status === 'success') {
        setAppliedFixes(prev => ({ ...prev, [index]: 'applied' }))
        if (res.data.updated_content) {
          setCodeContent(res.data.updated_content)
        }
      }
    } catch (err) {
      console.error('Apply fix error:', err)
    }
  }

  const handleAddComment = async (finding, index) => {
    if (!finding.suggestion || !file) return
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('line', finding.line || 1)
      formData.append('suggestion', finding.suggestion)

      const res = await axios.post('/add-suggestion-comment', formData)
      if (res.data.status === 'success') {
        setAppliedFixes(prev => ({ ...prev, [index]: 'commented' }))
        if (res.data.updated_content) {
          setCodeContent(res.data.updated_content)
        }
      }
    } catch (err) {
      console.error('Add comment error:', err)
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Live Code Intelligence Scanner</h2>
          <p className="text-sm text-gray-400">Scan Local Files or GitHub Repositories directly</p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex bg-gray-900/80 p-1 rounded-xl border border-gray-800 text-xs">
          <button
            onClick={() => setScanMode('file')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center space-x-2 ${
              scanMode === 'file' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>File / Code Upload</span>
          </button>

          <button
            onClick={() => setScanMode('github')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center space-x-2 ${
              scanMode === 'github' ? 'bg-purple-600 text-white shadow' : 'text-gray-400 hover:text-white'
            }`}
          >
            <Github className="w-3.5 h-3.5" />
            <span>GitHub Repo URL</span>
          </button>
        </div>
      </div>

      {/* Input Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Upload & Code Editor Box or GitHub Input */}
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          
          {scanMode === 'file' ? (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                  <FileCode className="w-4 h-4 text-blue-400" />
                  <span>Target Source Code</span>
                </h3>
                {file && (
                  <span className="text-xs font-mono text-blue-400 px-2 py-0.5 bg-blue-500/10 rounded">
                    {file.name}
                  </span>
                )}
              </div>

              {/* File Dropzone */}
              <label className="border-2 border-dashed border-gray-700 hover:border-blue-500/50 rounded-xl p-4 flex flex-col items-center justify-center cursor-pointer transition-all bg-gray-900/40">
                <Upload className="w-6 h-6 text-gray-400 mb-2" />
                <span className="text-xs text-gray-300 font-medium">Click to select Python file</span>
                <span className="text-[10px] text-gray-500 font-mono mt-1">.py files supported</span>
                <input type="file" accept=".py,.txt" onChange={handleFileChange} className="hidden" />
              </label>

              {/* Code Textarea */}
              <textarea
                value={codeContent}
                onChange={(e) => setCodeContent(e.target.value)}
                placeholder="Or paste code here directly..."
                rows={12}
                className="w-full bg-gray-950/80 border border-gray-800 rounded-xl p-4 text-xs font-mono text-gray-200 focus:outline-none focus:border-blue-500/50 resize-none"
              ></textarea>
            </>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center space-x-2 text-purple-400 font-semibold text-sm">
                <Github className="w-4 h-4" />
                <span className="text-white">Audit Remote GitHub Repository</span>
              </div>
              <p className="text-xs text-gray-400">
                Clone and run multi-engine security audits on any public or private GitHub repository.
              </p>

              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">GITHUB REPOSITORY URL</label>
                <div className="relative">
                  <Link className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/username/repository"
                    className="w-full bg-gray-950 border border-gray-800 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">BRANCH NAME</label>
                <input
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main or master"
                  className="w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-xl text-xs text-purple-300">
                💡 The system will clone the repository, run SAST, DAST, and LLM scans across all Python files, and store the audit report in MongoDB.
              </div>
            </div>
          )}

          {/* Run Button */}
          <button
            onClick={handleRunScan}
            disabled={scanning}
            className="w-full py-3 bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-600/20 flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
          >
            {scanning ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                <span>{scanMode === 'github' ? 'Cloning & Auditing Repo...' : 'Executing Multi-Engine Audit...'}</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>{scanMode === 'github' ? 'Audit GitHub Repository' : 'Run Code Audit'}</span>
              </>
            )}
          </button>

          {error && (
            <p className="text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">{error}</p>
          )}
        </div>

        {/* Verdict & Summary View */}
        <div className="glass-panel p-6 rounded-2xl space-y-6 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white mb-4">Audit Verdict & Security Score</h3>
            
            {scanResult ? (
              <div className="space-y-6">
                
                {/* Verdict Badge */}
                <div className={`p-6 rounded-2xl border flex items-center space-x-4 ${
                  scanResult.status === 'critical' || scanResult.verdict?.decision === 'BLOCK'
                    ? 'bg-red-950/30 border-red-500/40 text-red-400'
                    : scanResult.status === 'warning' || scanResult.verdict?.decision === 'WARN'
                    ? 'bg-yellow-950/30 border-yellow-500/40 text-yellow-400'
                    : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-400'
                }`}>
                  {scanResult.status === 'critical' || scanResult.verdict?.decision === 'BLOCK' ? (
                    <ShieldAlert className="w-10 h-10 flex-shrink-0" />
                  ) : scanResult.status === 'warning' || scanResult.verdict?.decision === 'WARN' ? (
                    <AlertTriangle className="w-10 h-10 flex-shrink-0" />
                  ) : (
                    <CheckCircle className="w-10 h-10 flex-shrink-0" />
                  )}
                  <div>
                    <h4 className="text-xl font-bold font-mono">
                      VERDICT: {scanResult.status?.toUpperCase() || scanResult.verdict?.decision || 'PASSED'}
                    </h4>
                    <p className="text-xs opacity-90">{scanResult.message || scanResult.verdict?.reason}</p>
                  </div>
                </div>

                {/* Engine Summary Pills */}
                {scanResult.summary ? (
                  <div className="space-y-2 text-xs font-mono">
                    <div className="p-3 bg-gray-900 rounded-xl border border-gray-800 flex justify-between">
                      <span>FILES ANALYZED</span>
                      <span className="text-white">{scanResult.files_analyzed}</span>
                    </div>
                    <div className="p-3 bg-gray-900 rounded-xl border border-gray-800 flex justify-between">
                      <span>TOTAL ISSUES DETECTED</span>
                      <span className="text-yellow-400">{scanResult.summary?.total_issues}</span>
                    </div>
                    <div className="p-3 bg-gray-900 rounded-xl border border-gray-800 flex justify-between">
                      <span>CRITICAL VULNERABILITIES</span>
                      <span className="text-red-400">{scanResult.summary?.critical_issues}</span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
                      <span className="flex items-center space-x-2 text-gray-300">
                        <Cpu className="w-4 h-4 text-blue-400" />
                        <span>SAST Static Engine</span>
                      </span>
                      <span className="font-mono text-blue-400">
                        {scanResult.engines?.sast?.findings?.length || 0} Issues
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
                      <span className="flex items-center space-x-2 text-gray-300">
                        <Zap className="w-4 h-4 text-purple-400" />
                        <span>DAST Dynamic Engine</span>
                      </span>
                      <span className="font-mono text-purple-400">
                        {scanResult.engines?.dast?.findings?.length || 0} Dynamic Risks
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
                      <span className="flex items-center space-x-2 text-gray-300">
                        <Sparkles className="w-4 h-4 text-cyan-400" />
                        <span>LLM Governance Review</span>
                      </span>
                      <span className="font-mono text-cyan-400">
                        {scanResult.engines?.governance?.findings?.length || 0} Violations
                      </span>
                    </div>
                  </div>
                )}

              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-center text-gray-500 space-y-2">
                <FileCode className="w-12 h-12 stroke-1" />
                <p className="text-sm">Select a file, enter code, or paste a GitHub URL to start audit.</p>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Detailed Findings List */}
      {scanResult && (
        <div className="glass-panel p-6 rounded-2xl space-y-6">
          <h3 className="text-lg font-bold text-white">Detected Findings & Remediation</h3>

          {/* GitHub Files Breakdown */}
          {scanResult.files?.map((fileItem, fIdx) => (
            <div key={`file-${fIdx}`} className="glass-card p-5 rounded-xl border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-blue-400 font-mono">{fileItem.path}</span>
                <span className="text-xs text-gray-400 font-mono">{fileItem.findings_count || 0} issues</span>
              </div>

              {fileItem.engines?.governance?.findings?.map((finding, idx) => (
                <div key={`file-gov-${idx}`} className="p-3 bg-red-950/20 border-l-2 border-red-500 rounded text-xs space-y-1">
                  <div className="flex items-center justify-between text-red-400 font-semibold">
                    <span>{finding.rule} (Line {finding.line})</span>
                    <span>{finding.severity}</span>
                  </div>
                  <p className="text-gray-300">{finding.message}</p>
                </div>
              ))}
            </div>
          ))}

          {/* Single Upload Governance Findings */}
          {scanResult.engines?.governance?.findings?.map((finding, idx) => (
            <div key={`gov-${idx}`} className="glass-card p-5 rounded-xl border-l-4 border-l-red-500 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs font-mono font-bold">
                    {finding.severity || 'HIGH'}
                  </span>
                  <span className="text-sm font-semibold text-white">{finding.rule}</span>
                  {finding.line && (
                    <span className="text-xs text-gray-400 font-mono">Line {finding.line}</span>
                  )}
                </div>
              </div>

              <p className="text-xs text-gray-300">{finding.message}</p>

              {finding.suggestion && (
                <div className="text-xs text-blue-300 bg-blue-950/30 p-2.5 rounded-lg border border-blue-500/20 flex items-start space-x-2">
                  <CornerDownRight className="w-4 h-4 flex-shrink-0 text-blue-400 mt-0.5" />
                  <span>{finding.suggestion}</span>
                </div>
              )}

              {finding.newCode && (
                <div className="space-y-1.5 pt-2">
                  <span className="text-[10px] font-mono text-emerald-400 uppercase">Suggested Code Fix:</span>
                  <pre className="p-3 bg-gray-950 rounded-lg text-xs font-mono text-emerald-300 overflow-x-auto border border-emerald-500/20">
                    {finding.newCode}
                  </pre>
                </div>
              )}

              <div className="pt-2 flex items-center space-x-3">
                {finding.newCode && (
                  <button
                    onClick={() => handleApplyFix(finding, `gov-${idx}`)}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg flex items-center space-x-1.5 transition-all"
                  >
                    {appliedFixes[`gov-${idx}`] === 'applied' ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Fix Applied</span>
                      </>
                    ) : (
                      <span>Apply Auto-Fix</span>
                    )}
                  </button>
                )}

                {finding.suggestion && (
                  <button
                    onClick={() => handleAddComment(finding, `gov-${idx}`)}
                    className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium rounded-lg flex items-center space-x-1.5 transition-all border border-gray-700"
                  >
                    <span>Insert Comment</span>
                  </button>
                )}
              </div>
            </div>
          ))}

          {/* SAST Findings */}
          {scanResult.engines?.sast?.findings?.map((finding, idx) => (
            <div key={`sast-${idx}`} className="glass-card p-5 rounded-xl border-l-4 border-l-blue-500 space-y-3">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 text-xs font-mono font-bold">
                  {finding.severity || 'HIGH'}
                </span>
                <span className="text-sm font-semibold text-white">{finding.rule}</span>
                <span className="text-xs text-gray-400 font-mono">Line {finding.line}</span>
              </div>
              <p className="text-xs text-gray-300">{finding.message}</p>
            </div>
          ))}

          {/* DAST Findings */}
          {scanResult.engines?.dast?.findings?.map((finding, idx) => (
            <div key={`dast-${idx}`} className="glass-card p-5 rounded-xl border-l-4 border-l-purple-500 space-y-3">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-400 text-xs font-mono font-bold">
                  {finding.severity || 'MEDIUM'}
                </span>
                <span className="text-sm font-semibold text-white">{finding.issue}</span>
              </div>
              <p className="text-xs text-gray-300">{finding.details}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
