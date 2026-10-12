import React, { useState, useEffect } from 'react';
import {
  Folder,
  FolderOpen,
  FileCode,
  ChevronRight,
  ChevronDown,
  Search,
  Copy,
  Check,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Code,
  AlertTriangle,
} from 'lucide-react';
import { ApiService } from '../services/api';
import type { ScanDirectoryInfo, FileNode, Finding, AiReviewSummary, AiReviewItem } from '../types';
import { SeverityBadge } from './SeverityBadge';

interface Props {
  scanId: string;
  directoryInfo: ScanDirectoryInfo | null;
  findings: Finding[];
  aiReviews: AiReviewSummary | null;
}

export const DirectoryTreeExplorer: React.FC<Props> = ({
  scanId,
  directoryInfo,
  findings,
  aiReviews,
}) => {
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileLines, setFileLines] = useState<number>(0);
  const [loadingContent, setLoadingContent] = useState(false);
  const [copiedPath, setCopiedPath] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedPatchId, setCopiedPatchId] = useState<string | null>(null);

  // Auto-select first file with vulnerabilities or first file available
  useEffect(() => {
    if (directoryInfo?.files && directoryInfo.files.length > 0 && !selectedFilePath) {
      const vulnFile = directoryInfo.files.find((f) => f.findings_count > 0);
      const initial = vulnFile || directoryInfo.files[0];
      setSelectedFilePath(initial.path);
    }
  }, [directoryInfo, selectedFilePath]);

  // Load content when selected file changes
  useEffect(() => {
    if (!selectedFilePath || !scanId) {
      setFileContent(null);
      return;
    }

    let isMounted = true;
    setLoadingContent(true);
    ApiService.getScanFileContent(scanId, selectedFilePath)
      .then((res) => {
        if (isMounted) {
          setFileContent(res.content || '');
          setFileLines(res.lines || 0);
        }
      })
      .catch(() => {
        if (isMounted) {
          setFileContent(null);
          setFileLines(0);
        }
      })
      .finally(() => {
        if (isMounted) setLoadingContent(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedFilePath, scanId]);

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => ({
      ...prev,
      [path]: prev[path] === false ? true : false,
    }));
  };

  const handleCopyPath = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleCopyPatch = (patchId: string, patchText: string) => {
    navigator.clipboard.writeText(patchText);
    setCopiedPatchId(patchId);
    setTimeout(() => setCopiedPatchId(null), 2000);
  };

  // Findings for the selected file
  const selectedFileFindings = findings.filter((f) => {
    if (!selectedFilePath || !f.file_path) return false;
    const cleanP = f.file_path.replace(/\\/g, '/').replace(/^\//, '');
    const cleanSel = selectedFilePath.replace(/\\/g, '/').replace(/^\//, '');
    return cleanP === cleanSel || cleanP.endsWith(cleanSel) || cleanSel.endsWith(cleanP);
  });

  // AI patch for a finding
  const getReviewForFinding = (finding: Finding): AiReviewItem | undefined => {
    if (!aiReviews?.recommendations) return undefined;
    return aiReviews.recommendations.find(
      (r) =>
        r.linked_finding_id === finding.id ||
        Boolean(finding.file_path && r.file_path && r.file_path.includes(finding.file_path))
    );
  };

  // Filter files if search is active
  const filteredFiles = (directoryInfo?.files || []).filter((f) =>
    searchFilter ? f.path.toLowerCase().includes(searchFilter.toLowerCase()) : true
  );

  // Recursive Tree Node Renderer
  const renderTreeNode = (node: FileNode, depth = 0): React.ReactNode => {
    const isExpanded = expandedFolders[node.path] !== false; // default expanded

    if (node.type === 'directory') {
      return (
        <div key={`dir-${node.path || node.name}`} className="select-none">
          <div
            onClick={() => toggleFolder(node.path)}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-slate-100/80 cursor-pointer text-xs font-semibold text-slate-700 transition-colors"
            style={{ paddingLeft: `${Math.max(8, depth * 14)}px` }}
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 text-amber-500 shrink-0" />
            ) : (
              <Folder className="w-4 h-4 text-amber-500 shrink-0" />
            )}
            <span className="truncate flex-1 font-mono text-[11px]">{node.name}</span>
            {node.findings_count > 0 && (
              <span className="px-1.5 py-0.2 text-[10px] font-bold rounded-full bg-red-100 text-red-700 shrink-0">
                {node.findings_count}
              </span>
            )}
          </div>
          {isExpanded && node.children && (
            <div className="border-l border-slate-100 ml-3">
              {node.children.map((child) => renderTreeNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    // File Node
    const isSelected = selectedFilePath === node.path;
    return (
      <div
        key={`file-${node.path}`}
        onClick={() => setSelectedFilePath(node.path)}
        className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg cursor-pointer text-xs transition-colors my-0.5 ${
          isSelected
            ? 'bg-blue-600 text-white font-bold shadow-2xs'
            : 'hover:bg-slate-100 text-slate-700 font-medium'
        }`}
        style={{ paddingLeft: `${Math.max(8, depth * 14 + 10)}px` }}
      >
        <FileCode
          className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-white' : 'text-slate-400'}`}
        />
        <span className="truncate flex-1 font-mono text-[11px]">{node.name}</span>
        {node.size ? (
          <span
            className={`text-[10px] shrink-0 ${
              isSelected ? 'text-blue-100' : 'text-slate-400'
            }`}
          >
            {formatBytes(node.size)}
          </span>
        ) : null}
        {node.findings_count > 0 && (
          <span
            className={`px-1.5 py-0.2 text-[10px] font-bold rounded-full shrink-0 ${
              isSelected ? 'bg-white text-red-600' : 'bg-red-100 text-red-700'
            }`}
          >
            {node.findings_count}
          </span>
        )}
      </div>
    );
  };

  const selectedFileMeta = directoryInfo?.files?.find((f) => f.path === selectedFilePath);

  return (
    <div className="space-y-4">
      {/* Search and Tree Controls Header */}
      <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Search files in uploaded directory..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="font-semibold text-slate-700">
            {directoryInfo?.total_files || 0} Files
          </span>
          &bull;
          <span>{directoryInfo?.total_directories || 1} Folders</span>
          &bull;
          <span>{formatBytes(directoryInfo?.total_size_bytes || 0)} Total</span>
        </div>
      </div>

      {/* Main 2-Column Explorer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Directory Tree / File List */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200 shadow-2xs p-3 overflow-hidden flex flex-col max-h-[650px]">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 px-1 mb-2">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <Folder className="w-3.5 h-3.5 text-blue-600" />
              <span>Project Files</span>
            </span>
            <span className="text-[11px] font-semibold text-slate-400">
              {filteredFiles.length} item{filteredFiles.length === 1 ? '' : 's'}
            </span>
          </div>

          <div className="overflow-y-auto flex-1 pr-1 space-y-0.5">
            {searchFilter ? (
              // Flat list when searching
              filteredFiles.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-400">
                  No files match &quot;{searchFilter}&quot;
                </div>
              ) : (
                filteredFiles.map((file) => {
                  const isSelected = selectedFilePath === file.path;
                  return (
                    <div
                      key={file.path}
                      onClick={() => setSelectedFilePath(file.path)}
                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg cursor-pointer text-xs transition-colors ${
                        isSelected
                          ? 'bg-blue-600 text-white font-bold shadow-2xs'
                          : 'hover:bg-slate-100 text-slate-700 font-medium'
                      }`}
                    >
                      <FileCode
                        className={`w-3.5 h-3.5 shrink-0 ${
                          isSelected ? 'text-white' : 'text-slate-400'
                        }`}
                      />
                      <span className="truncate flex-1 font-mono text-[11px]">{file.path}</span>
                      {file.findings_count > 0 && (
                        <span
                          className={`px-1.5 py-0.2 text-[10px] font-bold rounded-full shrink-0 ${
                            isSelected ? 'bg-white text-red-600' : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {file.findings_count}
                        </span>
                      )}
                    </div>
                  );
                })
              )
            ) : directoryInfo?.tree ? (
              // Hierarchical tree when not searching
              renderTreeNode(directoryInfo.tree)
            ) : (
              <div className="text-center py-8 text-xs text-slate-400">
                No files found in workspace directory.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: File Details, Security Findings & Code Preview */}
        <div className="lg:col-span-8 space-y-4">
          {selectedFilePath ? (
            <>
              {/* File Header Bar */}
              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`p-2 rounded-xl shrink-0 ${
                      selectedFileFindings.length > 0
                        ? 'bg-red-50 text-red-600 border border-red-100'
                        : 'bg-emerald-50 text-emerald-600 border border-emerald-100'
                    }`}
                  >
                    {selectedFileFindings.length > 0 ? (
                      <ShieldAlert className="w-4 h-4" />
                    ) : (
                      <ShieldCheck className="w-4 h-4" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-mono font-bold text-slate-900 truncate">
                      {selectedFilePath}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-2">
                      <span>{formatBytes(selectedFileMeta?.size || 0)}</span>
                      &bull;
                      <span>{fileLines || selectedFileMeta?.lines || 0} lines</span>
                      &bull;
                      <span
                        className={
                          selectedFileFindings.length > 0
                            ? 'font-bold text-red-600'
                            : 'font-semibold text-emerald-600'
                        }
                      >
                        {selectedFileFindings.length > 0
                          ? `${selectedFileFindings.length} Vulnerabilities Found`
                          : 'Clean File'}
                      </span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleCopyPath(selectedFilePath)}
                    className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
                  >
                    {copiedPath ? (
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <Copy className="w-3.5 h-3.5 text-slate-500" />
                    )}
                    <span>{copiedPath ? 'Copied Path!' : 'Copy Path'}</span>
                  </button>
                </div>
              </div>

              {/* Findings & AI Corrected Fixes for this File */}
              {selectedFileFindings.length > 0 && (
                <div className="bg-white p-4 rounded-2xl border border-red-200/80 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-red-100">
                    <span className="text-xs font-bold text-red-800 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-red-600" />
                      <span>Security Findings in {selectedFilePath}</span>
                    </span>
                    <span className="text-xs font-bold text-red-700 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">
                      {selectedFileFindings.length} issue{selectedFileFindings.length === 1 ? '' : 's'}
                    </span>
                  </div>

                  <div className="space-y-3">
                    {selectedFileFindings.map((finding) => {
                      const review = getReviewForFinding(finding);
                      const suggestedPatch = review?.patch?.suggested_code || review?.patch?.diff_unified || finding.suggested_fix;

                      return (
                        <div
                          key={finding.id}
                          className="p-3.5 bg-slate-50/80 rounded-xl border border-slate-200/80 space-y-2.5"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <SeverityBadge severity={finding.severity} />
                                <span className="text-[11px] font-mono text-slate-500 font-semibold">
                                  {finding.rule_id}
                                </span>
                                {finding.line_number && (
                                  <span className="text-[11px] font-mono text-slate-400">
                                    Line {finding.line_number}
                                  </span>
                                )}
                              </div>
                              <h4 className="text-xs font-bold text-slate-900">{finding.title}</h4>
                            </div>
                          </div>

                          <p className="text-xs text-slate-600 leading-relaxed">
                            {finding.description}
                          </p>

                          {/* AI Corrected Code Fix */}
                          {suggestedPatch && (
                            <div className="p-3 rounded-xl bg-purple-50/70 border border-purple-200/80 space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-[11px] font-bold text-purple-900 uppercase tracking-wider flex items-center gap-1.5">
                                  <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                                  <span>AI Corrected Code Suggestion</span>
                                </span>
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleCopyPatch(finding.id, suggestedPatch)
                                  }
                                  className="px-2 py-1 bg-white hover:bg-purple-100/60 text-purple-700 text-[11px] font-bold rounded-lg border border-purple-200 transition-colors flex items-center gap-1 cursor-pointer"
                                >
                                  {copiedPatchId === finding.id ? (
                                    <Check className="w-3 h-3 text-emerald-600" />
                                  ) : (
                                    <Copy className="w-3 h-3 text-purple-500" />
                                  )}
                                  <span>{copiedPatchId === finding.id ? 'Copied!' : 'Copy Fix'}</span>
                                </button>
                              </div>

                              <pre className="p-2.5 bg-slate-900 text-slate-100 rounded-lg text-[11px] font-mono overflow-x-auto leading-relaxed border border-slate-800">
                                <code>{suggestedPatch}</code>
                              </pre>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Source Code Viewer Box */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 bg-slate-50 border-b border-slate-200">
                  <div className="flex items-center gap-2">
                    <Code className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-xs font-bold text-slate-700">File Preview</span>
                    <span className="text-[11px] font-mono text-slate-400">
                      ({fileLines} lines)
                    </span>
                  </div>

                  {fileContent && (
                    <button
                      type="button"
                      onClick={() => handleCopyCode(fileContent)}
                      className="px-2 py-1 bg-white hover:bg-slate-100 text-slate-600 text-[11px] font-semibold rounded-lg border border-slate-200 transition-colors flex items-center gap-1 cursor-pointer"
                    >
                      {copiedCode ? (
                        <Check className="w-3 h-3 text-emerald-600" />
                      ) : (
                        <Copy className="w-3 h-3 text-slate-400" />
                      )}
                      <span>{copiedCode ? 'Copied!' : 'Copy Code'}</span>
                    </button>
                  )}
                </div>

                <div className="p-3 bg-slate-950 font-mono text-[11px] leading-relaxed text-slate-200 overflow-x-auto max-h-[480px]">
                  {loadingContent ? (
                    <div className="text-center py-10 text-slate-500">Loading file content...</div>
                  ) : fileContent ? (
                    <div className="table w-full">
                      {fileContent.split('\n').map((line, idx) => {
                        const lineNum = idx + 1;
                        const hasFindingOnLine = selectedFileFindings.some(
                          (f) => f.line_number === lineNum
                        );
                        return (
                          <div
                            key={lineNum}
                            className={`table-row ${
                              hasFindingOnLine ? 'bg-red-950/60 text-red-200 font-bold' : ''
                            }`}
                          >
                            <span className="table-cell select-none pr-4 text-right text-slate-600 w-10 shrink-0">
                              {lineNum}
                            </span>
                            <span className="table-cell whitespace-pre">{line || ' '}</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-10 text-slate-500">
                      File content preview is unavailable or binary format.
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs">
              Select a file from the left to inspect its directory path, findings, and code preview.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
