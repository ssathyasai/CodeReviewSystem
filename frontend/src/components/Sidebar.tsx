import React from 'react';
import {
  ShieldAlert,
  PlayCircle,
  FileText,
  Settings,
  ShieldCheck,
} from 'lucide-react';

interface Props {
  currentView: string;
  onNavigate: (view: string) => void;
  activeScanId?: string | null;
}

export const Sidebar: React.FC<Props> = ({ currentView, onNavigate, activeScanId }) => {
  const navItems = [
    { id: 'new-scan', label: 'New Scan', icon: PlayCircle, badge: 'Pipeline' },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-screen sticky top-0 select-none z-20">
      {/* Brand Logo & Name */}
      <div className="p-5 border-b border-slate-100 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-200">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-base font-bold text-slate-900 tracking-tight leading-tight">
            AI Code Review
          </h1>
          <p className="text-xs text-slate-500 font-medium">Security QA Platform</p>
        </div>
      </div>

      {/* Navigation List - Only New Scan, Reports, Settings */}
      <nav className="flex-1 px-3 py-5 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-sm font-semibold transition-all cursor-pointer ${
                isActive
                  ? 'bg-blue-600 text-white shadow-xs shadow-blue-200'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <Icon
                className={`w-4 h-4 shrink-0 transition-colors ${
                  isActive ? 'text-white' : 'text-slate-400'
                }`}
              />
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge && (
                <span
                  className={`px-1.5 py-0.5 text-[10px] font-bold rounded-md ${
                    isActive ? 'bg-blue-500/80 text-white' : 'bg-blue-50 text-blue-700'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Active Scan Indicator */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50">
        <div className="p-3 bg-white border border-slate-200/80 rounded-xl shadow-xs">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 mb-1">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>Pipeline Engine</span>
          </div>
          <p className="text-[11px] text-slate-500 truncate">
            {activeScanId ? (
              <span className="text-blue-600 font-mono font-medium truncate block">
                {activeScanId}
              </span>
            ) : (
              'Ready for code review'
            )}
          </p>
        </div>
      </div>
    </aside>
  );
};
