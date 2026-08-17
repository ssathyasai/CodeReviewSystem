import React, { useState, useEffect } from 'react'
import { History, Search, Eye, AlertTriangle, CheckCircle, ShieldAlert, X } from 'lucide-react'
import axios from 'axios'

export default function ScanHistory() {
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedScan, setSelectedScan] = useState(null)

  useEffect(() => {
    fetchScanHistory()
  }, [])

  const fetchScanHistory = async () => {
    try {
      setLoading(true)
      const res = await axios.get('/scans?limit=50')
      setScans(res.data.scans || [])
    } catch (err) {
      console.error('Error fetching scan history:', err)
    } finally {
      setLoading(false)
    }
  }

  const filteredScans = scans.filter(scan => {
    const target = scan.file || scan.project_name || scan.scan_id || ''
    return target.toLowerCase().includes(searchTerm.toLowerCase())
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Scan History & Audit Logs</h2>
          <p className="text-sm text-gray-400">Stored scan records retrieved from MongoDB</p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search scans..."
            className="bg-gray-950 border border-gray-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-blue-500 w-64"
          />
        </div>
      </div>

      {/* History Table */}
      <div className="glass-panel p-6 rounded-2xl">
        {loading ? (
          <p className="text-xs text-gray-500 py-12 text-center">Loading audit history from MongoDB...</p>
        ) : filteredScans.length === 0 ? (
          <div className="text-center py-12 text-gray-500 space-y-2">
            <History className="w-10 h-10 mx-auto stroke-1" />
            <p className="text-xs">No matching scan history found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-gray-400 uppercase bg-gray-800/40 font-mono">
                <tr>
                  <th className="px-4 py-3">Scan ID</th>
                  <th className="px-4 py-3">Target</th>
                  <th className="px-4 py-3">Verdict</th>
                  <th className="px-4 py-3">Engine Findings</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {filteredScans.map((scan) => {
                  const decision = scan.verdict?.decision || (scan.can_deploy ? 'APPROVE' : 'BLOCK')
                  const sastCount = scan.engines?.sast?.findings?.length || 0
                  const dastCount = scan.engines?.dast?.findings?.length || 0
                  const govCount = scan.engines?.governance?.findings?.length || 0
                  const totalIssues = sastCount + dastCount + govCount

                  return (
                    <tr key={scan.scan_id || Math.random()} className="hover:bg-gray-800/30">
                      <td className="px-4 py-3 font-mono text-blue-400">{scan.scan_id?.slice(0, 8) || 'N/A'}</td>
                      <td className="px-4 py-3 text-white font-medium">{scan.file || scan.project_name || 'Uploaded Code'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full font-mono text-[10px] ${
                          decision === 'BLOCK'
                            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                            : decision === 'WARN'
                            ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                            : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        }`}>
                          {decision}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-300 font-mono">
                        {totalIssues > 0 ? (
                          <span className="text-yellow-400">{totalIssues} Total Issues</span>
                        ) : (
                          <span className="text-emerald-400">0 Issues</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400 font-mono">
                        {scan.timestamp ? new Date(scan.timestamp).toLocaleString() : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setSelectedScan(scan)}
                          className="px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-xs font-medium border border-gray-700 transition-all inline-flex items-center space-x-1"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Details</span>
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

      {/* Detail Modal */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="glass-panel bg-gray-900 border border-gray-700 rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white">Scan Details</h3>
                <p className="text-xs font-mono text-gray-400">ID: {selectedScan.scan_id}</p>
              </div>
              <button onClick={() => setSelectedScan(null)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div className="p-4 rounded-xl bg-gray-950 border border-gray-800 space-y-1">
                <p className="text-gray-400">TARGET: <span className="text-white">{selectedScan.file || selectedScan.project_name}</span></p>
                <p className="text-gray-400">TIMESTAMP: <span className="text-white">{selectedScan.timestamp}</span></p>
                <p className="text-gray-400">DECISION: <span className="text-blue-400">{selectedScan.verdict?.decision || 'N/A'}</span></p>
              </div>

              <div className="space-y-2">
                <h4 className="text-sm font-bold text-white font-sans">Raw Audit Response JSON</h4>
                <pre className="p-4 bg-gray-950 rounded-xl text-emerald-300 text-[11px] overflow-x-auto border border-gray-800 max-h-96">
                  {JSON.stringify(selectedScan, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
