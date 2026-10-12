import React, { useState, useEffect } from 'react';
import {
  Settings,
  Cpu,
  Database,
  Shield,
  Save,
  CheckCircle2,
  Server,
  KeyRound,
  Zap,
} from 'lucide-react';
import { ApiService } from '../services/api';

export const SettingsView: React.FC = () => {
  const [provider, setProvider] = useState('local');
  const [groqKey, setGroqKey] = useState('');
  const [groqModel, setGroqModel] = useState('llama-3.3-70b-versatile');
  const [openaiKey, setOpenaiKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [ollamaModel, setOllamaModel] = useState('qwen2.5-coder:latest');
  const [maxUploadMb, setMaxUploadMb] = useState(50);
  const [allowDastLocal, setAllowDastLocal] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [systemHealth, setSystemHealth] = useState<any>(null);

  useEffect(() => {
    ApiService.getHealth()
      .then((data) => setSystemHealth(data))
      .catch((err) => console.error(err));

    ApiService.getSettings()
      .then((data) => {
        if (data) {
          if (data.ai_provider) setProvider(data.ai_provider);
          if (data.groq_model) setGroqModel(data.groq_model);
          if (data.ollama_url) setOllamaUrl(data.ollama_url);
          if (data.ollama_model) setOllamaModel(data.ollama_model);
          if (data.max_upload_size_mb) setMaxUploadMb(data.max_upload_size_mb);
          if (data.dast_allow_local_targets !== undefined) setAllowDastLocal(data.dast_allow_local_targets);
        }
      })
      .catch((err) => console.error('Failed to load settings:', err));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await ApiService.updateSettings({
        ai_provider: provider,
        groq_api_key: groqKey,
        groq_model: groqModel,
        openai_api_key: openaiKey,
        gemini_api_key: geminiKey,
        ollama_url: ollamaUrl,
        ollama_model: ollamaModel,
        max_upload_size_mb: Number(maxUploadMb),
        dast_allow_local_targets: allowDastLocal,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save settings:', err);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl border border-blue-100">
            <Settings className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">System Settings & Configuration</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Configure AI review engines, LLM guardrails, storage paths, and security scan boundaries.
            </p>
          </div>
        </div>
      </div>

      {savedSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Configuration saved successfully. System preferences updated.</span>
        </div>
      )}

      {/* System Status Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-3">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
          <Server className="w-4 h-4 text-blue-600" />
          Backend Telemetry & Environment
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
            <p className="text-[11px] font-semibold text-slate-400 uppercase">Engine Status</p>
            <p className="text-sm font-bold text-emerald-600 mt-1 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              {systemHealth?.status || 'ONLINE'}
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
            <p className="text-[11px] font-semibold text-slate-400 uppercase">Database Mode</p>
            <p className="text-sm font-bold text-slate-800 mt-1 flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-blue-600" />
              {systemHealth?.database_mode || 'LocalDocumentStore'}
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
            <p className="text-[11px] font-semibold text-slate-400 uppercase">System Version</p>
            <p className="text-sm font-bold text-slate-800 mt-1 font-mono">
              v{systemHealth?.version || '2.0.0'}
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* AI Provider Section */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-5">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-600" />
              AI Code Review & Intelligence Provider
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Choose the language model used to generate root-cause explanations and security code patches.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {[
              { id: 'local', title: 'Local Engine', desc: 'Deterministic AST intelligence (Default, zero API cost)' },
              { id: 'groq', title: 'Groq Cloud', desc: 'Ultra-fast LPU inference (Llama 3.3, Qwen Coder)' },
              { id: 'ollama', title: 'Ollama (Qwen 2.5)', desc: 'Private local model (Qwen 2.5 Coder, Llama 3)' },
              { id: 'openai', title: 'OpenAI GPT-4o', desc: 'Cloud high-accuracy LLM review' },
              { id: 'gemini', title: 'Google Gemini', desc: 'Google Gemini security code intelligence' },
            ].map((opt) => (
              <label
                key={opt.id}
                onClick={() => setProvider(opt.id)}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                  provider === opt.id
                    ? 'border-purple-500 bg-purple-50/40 ring-2 ring-purple-500/20'
                    : 'border-slate-200 bg-slate-50/40 hover:bg-slate-50 hover:border-slate-300'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">{opt.title}</span>
                    <input
                      type="radio"
                      name="provider"
                      checked={provider === opt.id}
                      onChange={() => setProvider(opt.id)}
                      className="text-purple-600 focus:ring-purple-500"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">{opt.desc}</p>
                </div>
              </label>
            ))}
          </div>

          {/* Conditional provider inputs */}
          {provider === 'groq' && (
            <div className="pt-2 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5 text-purple-600" />
                  Groq API Key
                </label>
                <input
                  type="password"
                  value={groqKey}
                  onChange={(e) => setGroqKey(e.target.value)}
                  placeholder="gsk_xxxxxxxxxxxxxxxxxxxxxxxx"
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                />
                <p className="text-[11px] text-slate-400">Get your free high-speed API key at console.groq.com</p>
              </div>
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-500" />
                  Groq Model
                </label>
                <select
                  value={groqModel}
                  onChange={(e) => setGroqModel(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                >
                  <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Recommended)</option>
                  <option value="llama-3.1-8b-instant">llama-3.1-8b-instant (Fastest)</option>
                  <option value="qwen-2.5-coder-32b">qwen-2.5-coder-32b (Code Specialist)</option>
                  <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
                </select>
                <p className="text-[11px] text-slate-400">Model executed with millisecond latency on Groq LPUs</p>
              </div>
            </div>
          )}

          {provider === 'ollama' && (
            <div className="pt-2 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Ollama Endpoint URL
                </label>
                <input
                  type="text"
                  value={ollamaUrl}
                  onChange={(e) => setOllamaUrl(e.target.value)}
                  placeholder="http://localhost:11434"
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                />
                <p className="text-[11px] text-slate-400">Ensure Ollama service is running (`ollama serve`)</p>
              </div>
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Ollama Model (Qwen 2.5 Coder)
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={ollamaModel}
                    onChange={(e) => setOllamaModel(e.target.value)}
                    placeholder="qwen2.5-coder:latest"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  />
                </div>
                <p className="text-[11px] text-slate-400">e.g. `qwen2.5-coder:latest`, `qwen2.5:latest`, or `llama3.2:latest`</p>
              </div>
            </div>
          )}

          {provider === 'openai' && (
            <div className="pt-2 space-y-2">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                OpenAI API Key
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder="sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx"
                  className="w-full pl-9 pr-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                />
              </div>
            </div>
          )}

          {provider === 'gemini' && (
            <div className="pt-2 space-y-2">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Google Gemini API Key
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder="AIzaSyxxxxxxxxxxxxxxxxxxxxxxx"
                  className="w-full pl-9 pr-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                />
              </div>
            </div>
          )}
        </div>

        {/* Scanner Limits & Guardrails */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Shield className="w-4 h-4 text-blue-600" />
              Safety Boundaries & Scan Limits
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Limits prevent denial of service and block dangerous targets.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Max Upload Archive Size (MB)
              </label>
              <input
                type="number"
                value={maxUploadMb}
                onChange={(e) => setMaxUploadMb(Number(e.target.value))}
                min={1}
                max={500}
                className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              />
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50/50">
              <div>
                <span className="text-xs font-bold text-slate-800 block">Allow Localhost DAST Targets</span>
                <span className="text-[11px] text-slate-500">Permit http://localhost testing</span>
              </div>
              <input
                type="checkbox"
                checked={allowDastLocal}
                onChange={(e) => setAllowDastLocal(e.target.checked)}
                className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4 cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* Save button */}
        <div className="flex justify-end">
          <button
            type="submit"
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-xs shadow-blue-200 flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>Save Configuration</span>
          </button>
        </div>
      </form>
    </div>
  );
};
