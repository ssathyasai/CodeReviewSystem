import React, { useState, useEffect } from 'react'
import { History, Search, RefreshCw, Eye, CheckCircle, AlertTriangle, ShieldAlert, Code, FileText, X } from 'lucide-react'
import axios from 'axios'

export default function ScanHistory({ currentUser }) {
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedScan, setSelectedScan] = useState(null)

  useEffect(() => {
    fetchScans()
  }, [currentUser])

  const fetchScans = async () => {
    try {
      setLoading(true)
      if (!currentUser?.username) {
        setScans([])
        setLoading(false)
        return
      }
      const res = await axios.get(`/scans?username=${currentUser.username}`)
      setScans(res.data.scans || [])
    } catch (err) {
      console.error('Failed to fetch scan history:', err)
    } finally {
      setLoading(false)
    }
  }

  const filteredScans = scans.filter(scan => {
    const term = search.toLowerCase()
    const target = (scan.file || scan.repository || scan.project_name || '').toLowerCase()
    const scanId = (scan.scan_id || '').toLowerCase()
    return target.includes(term) || scanId.includes(term)
  })

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-box p-6 rounded-3xl">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-2xl border border-purple-500/20">
            <History className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-white">Historical Security Audit Records</h2>
            <p className="text-xs text-slate-400">Stored scan history retrieved from MongoDB Atlas</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by file or scan ID..."
              className="pl-9 pr-4 py-2 bg-slate-900/90 border border-slate-800 rounded-xl text-slate-200 text-xs font-mono focus:outline-none focus:border-purple-500"
            />
          </div>
          <button
            onClick={fetchScans}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="glass-box rounded-3xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 font-mono text-xs space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-purple-400" />
            <p>Loading records from MongoDB...</p>
          </div>
        ) : filteredScans.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">
            No scan history records found matching "{search}".
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4">Scan ID</th>
                  <th className="px-6 py-4">Audit Target</th>
                  <th className="px-6 py-4">Verdict</th>
                  <th className="px-6 py-4">Issues Found</th>
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredScans.map((scan) => {
                  const decision = scan.verdict?.decision || (scan.status === 'critical' || scan.can_deploy === false ? 'BLOCK' : 'APPROVE')
                  const issues = scan.summary?.total_issues || scan.critical_count || 0
                  return (
                    <tr key={scan.scan_id || Math.random()} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-6 py-4 font-mono text-cyan-400 font-semibold">{scan.scan_id?.slice(0, 8) || 'N/A'}</td>
                      <td className="px-6 py-4 text-slate-200 font-medium">{scan.file || scan.repository || scan.project_name || 'Uploaded File'}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full font-mono text-[10px] font-bold ${
                          decision === 'BLOCK' ? 'badge-critical-glow' : decision === 'WARN' ? 'badge-warning-glow' : 'badge-success-glow'
                        }`}>
                          {decision}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-slate-300">{issues} issue(s)</td>
                      <td className="px-6 py-4 font-mono text-slate-400">{scan.timestamp ? new Date(scan.timestamp).toLocaleString() : 'N/A'}</td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => setSelectedScan(scan)}
                          className="px-3 py-1 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 text-xs font-medium border border-purple-500/30 transition-all flex items-center space-x-1.5 ml-auto"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Details</span>
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Audit Detail Modal */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0B111E] border border-slate-800 rounded-3xl max-w-3xl w-full p-6 space-y-4 max-h-[85vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="font-bold text-white text-lg">Audit Record Details</h3>
                <p className="text-xs text-slate-400 font-mono">Scan ID: {selectedScan.scan_id}</p>
              </div>
              <button onClick={() => setSelectedScan(null)} className="p-2 text-slate-400 hover:text-white rounded-xl bg-slate-800/60">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2 font-mono text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Target File / Repo:</span>
                  <span className="text-cyan-400 font-bold">{selectedScan.file || selectedScan.repository || selectedScan.project_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Verdict:</span>
                  <span className="text-white font-bold">{selectedScan.verdict?.decision || selectedScan.status}</span>
                </div>
              </div>

              <div className="space-y-1">
                <h4 className="text-xs font-mono text-slate-400">RAW AUDIT JSON DATA</h4>
                <pre className="p-4 rounded-2xl bg-[#070B14] border border-slate-800/80 text-cyan-300 font-mono text-xs overflow-x-auto max-h-64">
                  {JSON.stringify(selectedScan, null, 2)}
                </pre>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedScan(null)}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs border border-slate-700"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
