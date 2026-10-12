import React, { useEffect, useState } from 'react';
import {
  FileText,
  Download,
  FileCode,
  Calendar,
  RefreshCw,
  Search,
  CheckCircle2,
  FileCheck2,
} from 'lucide-react';
import { ApiService } from '../services/api';
import type { Scan } from '../types';
import { SeverityBadge } from '../components/SeverityBadge';

interface Props {
  activeScanId?: string | null;
  onSelectScan?: (scanId: string) => void;
}

export const ReportsView: React.FC<Props> = ({ activeScanId, onSelectScan }) => {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const fetchScans = async () => {
    setLoading(true);
    try {
      const res = await ApiService.listScans(undefined, 100);
      setScans(res.scans || []);
    } catch (err) {
      console.error('Failed to fetch scans for reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScans();
  }, []);

  const filteredScans = scans.filter((s) =>
    s.project_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDownloadPdf = (scanId: string) => {
    setDownloadingId(scanId);
    window.open(ApiService.getReportPdfUrl(scanId), '_blank');
    setTimeout(() => setDownloadingId(null), 2000);
  };

  const handleDownloadJson = (scanId: string) => {
    window.open(ApiService.getReportJsonUrl(scanId), '_blank');
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl border border-blue-100">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Security Assessment Reports</h2>
          </div>
          <p className="text-xs text-slate-500">
            Generate and export official compliance security audit reports in PDF and structured JSON formats.
          </p>
        </div>

        <button
          onClick={fetchScans}
          className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors self-start md:self-auto cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Reports</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search report by project name or scan ID..."
            className="w-full pl-9 pr-4 py-2 text-xs bg-white border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
        <span className="text-xs font-medium text-slate-500">
          {filteredScans.length} {filteredScans.length === 1 ? 'Report' : 'Reports'} available
        </span>
      </div>

      {/* Loading state */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3">
          <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
          <p className="text-xs font-medium text-slate-500">Loading audit reports catalog...</p>
        </div>
      ) : filteredScans.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-slate-200 shadow-2xs text-center space-y-3">
          <FileText className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700">No Reports Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Run a security scan from the <strong>New Scan</strong> tab to automatically compile an executive security report.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredScans.map((scan) => {
            const isCurrent = scan.id === activeScanId;
            return (
              <div
                key={scan.id}
                className={`bg-white p-6 rounded-2xl border transition-all ${
                  isCurrent
                    ? 'border-blue-400 ring-2 ring-blue-500/10 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 shadow-2xs'
                }`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
                  {/* Left: Project details */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="text-base font-bold text-slate-900">{scan.project_name}</span>
                      <span className="font-mono text-[11px] font-semibold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-100">
                        {scan.id}
                      </span>
                      {scan.status === 'COMPLETED' ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          Audit Completed
                        </span>
                      ) : (
                        <span className="text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                          {scan.status}
                        </span>
                      )}
                      {isCurrent && (
                        <span className="text-[10px] uppercase font-bold tracking-wider text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
                          Active Scan
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {new Date(scan.created_at).toLocaleDateString('en-GB', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      <span>&bull;</span>
                      <span>Source: <strong className="text-slate-700 font-medium">{scan.input_type}</strong></span>
                      <span>&bull;</span>
                      <span>Analyzed: <strong className="text-slate-700 font-medium">{scan.summary?.files_analyzed || 0} files</strong></span>
                    </div>

                    {/* Findings Breakdown Pills */}
                    {scan.summary && (
                      <div className="flex items-center gap-2 pt-1 flex-wrap">
                        <span className="text-xs font-semibold text-slate-700">
                          {scan.summary.total_findings} Vulnerabilities:
                        </span>
                        {scan.summary.critical > 0 && <SeverityBadge severity="CRITICAL" size="sm" />}
                        {scan.summary.high > 0 && <SeverityBadge severity="HIGH" size="sm" />}
                        {scan.summary.medium > 0 && <SeverityBadge severity="MEDIUM" size="sm" />}
                        {scan.summary.low > 0 && <SeverityBadge severity="LOW" size="sm" />}
                        {scan.summary.total_findings === 0 && (
                          <span className="text-xs text-emerald-600 font-medium">0 vulnerabilities detected</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Right: Actions */}
                  <div className="flex items-center gap-3 shrink-0">
                    {onSelectScan && (
                      <button
                        onClick={() => onSelectScan(scan.id)}
                        className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors cursor-pointer"
                      >
                        View in New Scan
                      </button>
                    )}

                    <button
                      onClick={() => handleDownloadPdf(scan.id)}
                      disabled={downloadingId === scan.id}
                      className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-xs shadow-blue-200 transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
                      title="Download formatted executive PDF report"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>{downloadingId === scan.id ? 'Opening PDF...' : 'Download PDF'}</span>
                    </button>

                    <button
                      onClick={() => handleDownloadJson(scan.id)}
                      className="px-4 py-2 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl transition-colors flex items-center gap-1.5 cursor-pointer"
                      title="Export raw JSON schema for SIEM or CI/CD pipelines"
                    >
                      <FileCode className="w-3.5 h-3.5 text-slate-500" />
                      <span>Export JSON</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
