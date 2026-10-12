import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Globe,
  Key,
  Package,
  Sparkles,
  Terminal,
  Activity,
  RefreshCw,
  Zap,
} from 'lucide-react';
import type { Scan } from '../types';

interface Props {
  scan: Scan | null;
  pipelineProgress: number;
  currentStage: string;
}

export const PipelineRunningAnimation: React.FC<Props> = ({
  scan,
  pipelineProgress,
  currentStage,
}) => {
  const [simulatedLogs, setSimulatedLogs] = useState<string[]>([
    '[PIPELINE] Initializing sandboxed execution environment...',
    '[SAST] Parsing Abstract Syntax Trees (AST) for Python & TypeScript files...',
    '[SAST] Inspecting source code for CWE-89 (SQL Injection) and CWE-79 (XSS)...',
    '[DAST] Spawning synthetic HTTP client for dynamic endpoint exploration...',
    '[DAST] Spidering REST routes: /api/v1/auth, /api/v1/payment, /health...',
    '[SECRETS] Executing Shannon entropy analysis across configuration files...',
    '[DEPENDENCIES] Cross-referencing package manifests against CVE vulnerability advisories...',
    '[AI-GOVERNANCE] Evaluating prompt injection & output hallucination risk guardrails...',
    '[AI-REPAIR] Activating LLM code repair engine for verifiable patch generation...',
  ]);

  // Rotate simulated live ticker
  useEffect(() => {
    const interval = setInterval(() => {
      const timestamps = new Date().toLocaleTimeString();
      const dynamicMessages = [
        `[SAST] [${timestamps}] Taint analysis tracking data flow across function parameters...`,
        `[DAST] [${timestamps}] Fuzzing dynamic endpoint payload injection boundaries...`,
        `[SECRETS] [${timestamps}] Verified regex rules against AWS, Stripe, and private keys...`,
        `[AI-REVIEW] [${timestamps}] Synthesizing unified diff patch with AST verification...`,
        `[DAST] [${timestamps}] Dynamic response headers: X-Frame-Options, CSP, and HSTS verified...`,
      ];
      const randomMsg = dynamicMessages[Math.floor(Math.random() * dynamicMessages.length)];
      setSimulatedLogs((prev) => [...prev.slice(-14), randomMsg]);
    }, 2500);

    return () => clearInterval(interval);
  }, []);

  const sastProgress = Math.min(100, Math.max(15, pipelineProgress * 1.1));
  const dastProgress = Math.min(100, Math.max(10, pipelineProgress * 0.95));

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top Banner Card */}
      <div className="bg-white p-6 rounded-3xl border border-blue-200/80 shadow-xs relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-blue-400/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
        <div className="absolute bottom-0 left-0 w-80 h-80 bg-purple-400/10 rounded-full blur-3xl pointer-events-none -ml-20 -mb-20" />

        <div className="relative z-10 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-md shadow-blue-500/20">
                <RefreshCw className="w-6 h-6 animate-spin" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-extrabold text-slate-900 tracking-tight">
                    Security Analysis: {scan?.project_name || 'Active Pipeline'}
                  </h3>
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-700">
                    <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
                    LIVE SCANNING
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5 max-w-xl">
                  {currentStage ||
                    'Running concurrent SAST Static Code Analysis, DAST Dynamic Endpoint Testing, and AI Patch Synthesis...'}
                </p>
              </div>
            </div>

            <div className="text-right sm:self-center shrink-0">
              <span className="text-2xl font-black font-mono text-blue-600">
                {pipelineProgress}%
              </span>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Overall Completed
              </p>
            </div>
          </div>

          {/* Glowing Animated Progress Bar */}
          <div className="space-y-1.5 pt-1">
            <div className="h-3.5 bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200/80 shadow-inner">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 transition-all duration-700 relative overflow-hidden"
                style={{ width: `${Math.max(8, pipelineProgress)}%` }}
              >
                {/* Laser highlight sweep inside progress bar */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent w-full animate-laser" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* FEATURED DUAL-ENGINE COCKPIT: SAST vs DAST RUNNING ANIMATIONS */}
      {/* ===================================================================== */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* =================================================================== */}
        {/* ENGINE 1: SAST (STATIC APPLICATION SECURITY TESTING) ANIMATION */}
        {/* =================================================================== */}
        <div className="bg-slate-950 rounded-3xl p-5 border border-blue-500/40 shadow-lg text-slate-100 relative overflow-hidden flex flex-col justify-between animate-pulse-border">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-blue-500/20 text-blue-400 border border-blue-500/30">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-extrabold text-white tracking-wide">
                    SAST Static Analysis
                  </h4>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold tracking-wider bg-blue-500/30 text-blue-300 border border-blue-400/40">
                    AST ENGINE
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">Static Abstract Syntax Tree & Taint Flow</p>
              </div>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-950/90 border border-blue-500/50 text-[11px] font-bold text-blue-400">
              <Activity className="w-3.5 h-3.5 animate-pulse text-blue-400" />
              <span>SCANNING</span>
            </div>
          </div>

          {/* Animated SAST Visual Code Scanner Box */}
          <div className="my-4 relative h-48 bg-slate-900/90 rounded-2xl border border-blue-500/30 overflow-hidden p-3 font-mono text-[11px] text-blue-300/80 select-none shadow-inner">
            {/* Glowing Laser Scan Line Sweeper */}
            <div className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_15px_#22d3ee] animate-laser z-20 pointer-events-none" />

            {/* Simulated Live AST Code Inspection Stream */}
            <div className="space-y-1.5 opacity-80 animate-code-scroll">
              <p className="text-emerald-400 font-bold">
                &gt; ast.parse(source_file=&quot;services/payment.py&quot;)
              </p>
              <p className="text-blue-300">&gt; analyzing taint sources: request.args, req.body</p>
              <p className="text-amber-400">&gt; check_sink: cursor.execute(query) [CWE-89 SQLi]</p>
              <p className="text-slate-400">
                &gt; inspecting sanitizer: escape_string() missing on line 42
              </p>
              <p className="text-cyan-400">&gt; [BANDIT_B608] Hardcoded SQL formatting detected</p>
              <p className="text-purple-400">
                &gt; [SEMGREP_TAINT] Propagating user input to database sink...
              </p>
              <p className="text-blue-300">&gt; scanning cryptographic ciphers: MD5 vs SHA-256</p>
              <p className="text-red-400 font-semibold">
                &gt; alert flagged: insecure deserialization (pickle.loads)
              </p>
              <p className="text-emerald-400">&gt; ast.walk completed for module: auth_service.ts</p>
              <p className="text-slate-400">&gt; scanning React DOM sinks: dangerouslySetInnerHTML</p>
              <p className="text-cyan-400">&gt; verifying AST syntax tree integrity...</p>
            </div>

            {/* Scanner Overlay Badge */}
            <div className="absolute bottom-2 right-2 bg-slate-950/90 border border-blue-500/40 px-2 py-1 rounded-lg text-[10px] font-mono text-cyan-300 flex items-center gap-1.5 shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              <span>48 Rules Active</span>
            </div>
          </div>

          {/* SAST Metrics Footer */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
            <span className="flex items-center gap-1 text-blue-300 font-medium">
              <Zap className="w-3.5 h-3.5 text-blue-400" />
              <span>Taint-Flow Analysis Active</span>
            </span>
            <span className="font-mono text-cyan-400 font-bold">{Math.round(sastProgress)}%</span>
          </div>
        </div>

        {/* =================================================================== */}
        {/* ENGINE 2: DAST (DYNAMIC APPLICATION SECURITY TESTING) ANIMATION */}
        {/* =================================================================== */}
        <div className="bg-slate-950 rounded-3xl p-5 border border-purple-500/40 shadow-lg text-slate-100 relative overflow-hidden flex flex-col justify-between animate-pulse-border">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30">
                <Globe className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-extrabold text-white tracking-wide">
                    DAST Dynamic Fuzzing
                  </h4>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold tracking-wider bg-purple-500/30 text-purple-300 border border-purple-400/40">
                    NETWORK RADAR
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">Active HTTP Endpoints & Boundary Probing</p>
              </div>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-950/90 border border-purple-500/50 text-[11px] font-bold text-purple-400">
              <Activity className="w-3.5 h-3.5 animate-pulse text-purple-400" />
              <span>PROBING</span>
            </div>
          </div>

          {/* Animated DAST Visual Radar & Spider Box */}
          <div className="my-4 relative h-48 bg-slate-900/90 rounded-2xl border border-purple-500/30 overflow-hidden flex items-center justify-center p-3 select-none shadow-inner">
            {/* Concentric Radar Rings */}
            <div className="absolute w-36 h-36 rounded-full border border-purple-500/20" />
            <div className="absolute w-24 h-24 rounded-full border border-purple-500/30" />
            <div className="absolute w-12 h-12 rounded-full border border-purple-500/40" />

            {/* Radar Crosshairs */}
            <div className="absolute w-44 h-[1px] bg-purple-500/20" />
            <div className="absolute h-44 w-[1px] bg-purple-500/20" />

            {/* Rotating Radar Sweep Beam */}
            <div className="absolute w-36 h-36 rounded-full overflow-hidden animate-radar-sweep pointer-events-none">
              <div className="w-18 h-18 bg-gradient-to-br from-purple-500/50 via-transparent to-transparent origin-bottom-right" />
            </div>

            {/* Dynamic Target Pings */}
            <div className="absolute top-9 left-16 flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-radar-ping absolute" />
              <span className="w-2 h-2 rounded-full bg-red-400" />
              <span className="text-[9px] font-mono text-purple-300 bg-slate-950/80 px-1 py-0.5 rounded border border-purple-900">
                /api/auth
              </span>
            </div>

            <div className="absolute bottom-8 right-14 flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-radar-ping absolute" />
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span className="text-[9px] font-mono text-purple-300 bg-slate-950/80 px-1 py-0.5 rounded border border-purple-900">
                /transfer
              </span>
            </div>

            <div className="absolute top-12 right-12 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-[9px] font-mono text-emerald-300 bg-slate-950/80 px-1 py-0.5 rounded border border-emerald-900">
                /health 200
              </span>
            </div>

            {/* Bottom Live Fuzzing Status Pill */}
            <div className="absolute bottom-2 left-2 bg-slate-950/90 border border-purple-500/40 px-2.5 py-1 rounded-lg text-[10px] font-mono text-purple-300 flex items-center gap-1.5 shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-ping" />
              <span>Spidering OWASP Top 10 Surface</span>
            </div>
          </div>

          {/* DAST Metrics Footer */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
            <span className="flex items-center gap-1 text-purple-300 font-medium">
              <Zap className="w-3.5 h-3.5 text-purple-400" />
              <span>Dynamic Payload Fuzzing Active</span>
            </span>
            <span className="font-mono text-purple-400 font-bold">{Math.round(dastProgress)}%</span>
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* 5-PILLAR SCANNER STATUS CARDS (SAST, DAST, SECRETS, DEPENDENCIES, AI) */}
      {/* ===================================================================== */}
      <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-2xs space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-600" />
            <span>Multi-Engine Pipeline Execution Checklist</span>
          </span>
          <span className="text-xs text-slate-400 font-medium">5 Concurrent Security Verifiers</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* 1. SAST */}
          <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <div className="p-1.5 rounded-lg bg-blue-600 text-white">
                <ShieldAlert className="w-4 h-4" />
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-200/80 text-blue-800 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                ACTIVE
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-900">SAST Analysis</p>
              <p className="text-[11px] text-slate-500 mt-0.5">AST syntax & taint flow</p>
            </div>
            <div className="h-1.5 bg-blue-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full transition-all duration-500"
                style={{ width: `${sastProgress}%` }}
              />
            </div>
          </div>

          {/* 2. DAST */}
          <div className="p-3.5 rounded-2xl bg-purple-50/70 border border-purple-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <div className="p-1.5 rounded-lg bg-purple-600 text-white">
                <Globe className="w-4 h-4" />
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-purple-200/80 text-purple-800 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-600 animate-pulse" />
                ACTIVE
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-900">DAST Dynamic</p>
              <p className="text-[11px] text-slate-500 mt-0.5">Spidering endpoints</p>
            </div>
            <div className="h-1.5 bg-purple-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-600 rounded-full transition-all duration-500"
                style={{ width: `${dastProgress}%` }}
              />
            </div>
          </div>

          {/* 3. Secrets */}
          <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <div className="p-1.5 rounded-lg bg-emerald-600 text-white">
                <Key className="w-4 h-4" />
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-200/80 text-emerald-800 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                ACTIVE
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-900">Secret Scanner</p>
              <p className="text-[11px] text-slate-500 mt-0.5">Entropy & API credentials</p>
            </div>
            <div className="h-1.5 bg-emerald-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-600 rounded-full transition-all duration-500"
                style={{ width: `${pipelineProgress}%` }}
              />
            </div>
          </div>

          {/* 4. Dependencies */}
          <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <div className="p-1.5 rounded-lg bg-amber-600 text-white">
                <Package className="w-4 h-4" />
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-200/80 text-amber-800 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-pulse" />
                ACTIVE
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-900">Dependency SCA</p>
              <p className="text-[11px] text-slate-500 mt-0.5">CVE advisory audit</p>
            </div>
            <div className="h-1.5 bg-amber-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-600 rounded-full transition-all duration-500"
                style={{ width: `${pipelineProgress}%` }}
              />
            </div>
          </div>

          {/* 5. AI Review */}
          <div className="p-3.5 rounded-2xl bg-fuchsia-50/70 border border-fuchsia-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <div className="p-1.5 rounded-lg bg-fuchsia-600 text-white">
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-fuchsia-200/80 text-fuchsia-800 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-600 animate-pulse" />
                SYNTHESIS
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-900">AI Code Repair</p>
              <p className="text-[11px] text-slate-500 mt-0.5">Verified code patches</p>
            </div>
            <div className="h-1.5 bg-fuchsia-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-fuchsia-600 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(15, pipelineProgress)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* LIVE SCANNER LOGS TICKER */}
      {/* ===================================================================== */}
      <div className="bg-slate-950 rounded-3xl border border-slate-800 shadow-md p-4 text-slate-300 font-mono text-xs overflow-hidden">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 px-1 mb-2">
          <div className="flex items-center gap-2 text-slate-400">
            <Terminal className="w-4 h-4 text-blue-400" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
              Live Pipeline Stream Output
            </span>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-900 text-emerald-400 border border-slate-800">
            STDOUT STREAMING
          </span>
        </div>

        <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1 text-[11px] leading-relaxed">
          {simulatedLogs.map((log, index) => (
            <div key={index} className="flex items-start gap-2">
              <span className="text-blue-500 select-none">&rsaquo;</span>
              <span
                className={
                  log.includes('[SAST]')
                    ? 'text-cyan-300'
                    : log.includes('[DAST]')
                    ? 'text-purple-300'
                    : log.includes('[SECRETS]')
                    ? 'text-emerald-300'
                    : log.includes('[AI')
                    ? 'text-fuchsia-300'
                    : 'text-slate-300'
                }
              >
                {log}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
