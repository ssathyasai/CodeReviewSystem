import React, { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import Dashboard from './components/Dashboard'
import Scanner from './components/Scanner'
import ScanHistory from './components/ScanHistory'
import GitHubSettings from './components/GitHubSettings'
import axios from 'axios'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [systemStatus, setSystemStatus] = useState(null)

  useEffect(() => {
    fetchSystemStatus()
  }, [])

  const fetchSystemStatus = async () => {
    try {
      const res = await axios.get('/llm/status')
      setSystemStatus(res.data)
    } catch (err) {
      console.error('Failed to fetch LLM status:', err)
    }
  }

  return (
    <div className="min-h-screen bg-[#0B0F17] text-gray-100 flex flex-col">
      {/* Header Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} systemStatus={systemStatus} />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && <Dashboard setActiveTab={setActiveTab} />}
        {activeTab === 'scanner' && <Scanner />}
        {activeTab === 'history' && <ScanHistory />}
        {activeTab === 'github' && <GitHubSettings />}
      </main>

      {/* Footer */}
      <footer className="glass-panel border-t border-gray-800 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-gray-500 font-mono">
          Hybrid Code Intelligence Agent &bull; Powered by MongoDB, FastAPI & React &bull; OWASP Compliant
        </div>
      </footer>
    </div>
  )
}
