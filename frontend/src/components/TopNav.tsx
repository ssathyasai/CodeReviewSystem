import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  PlayCircle,
} from 'lucide-react';
import { ApiService } from '../services/api';

interface Props {
  currentView: string;
  onNavigate: (view: string) => void;
  onRefresh?: () => void;
}

export const TopNav: React.FC<Props> = ({ currentView, onNavigate, onRefresh }) => {
  const [seeding, setSeeding] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);

  const getPageTitle = (view: string) => {
    const titles: Record<string, { title: string; subtitle: string }> = {
      'new-scan': { title: 'New Security Scan', subtitle: 'Submit a project via ZIP archive or GitHub repository.' },
      reports: { title: 'Security Reports & Exports', subtitle: 'Download executive compliance reports in PDF and JSON.' },
      settings: { title: 'System Configuration', subtitle: 'Scanner settings, AI model provider, and safety limits.' },
    };
    return titles[view] || { title: 'Security Pipeline', subtitle: 'AI Code Review & Quality Assurance Platform' };
  };

  const currentInfo = getPageTitle(currentView);

  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      await ApiService.seedDemoData();
      setSeedSuccess(true);
      if (onRefresh) onRefresh();
      setTimeout(() => setSeedSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-10">
      {/* Title & Breadcrumbs */}
      <div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">AI Code Review</span>
          <span className="text-slate-300">/</span>
          <h2 className="text-base font-bold text-slate-900">{currentInfo.title}</h2>
        </div>
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-3">
        {/* Load Demo Data Button */}
        <button
          type="button"
          onClick={handleSeedDemo}
          disabled={seeding}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-purple-200 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold transition-colors shadow-2xs cursor-pointer"
          title="Seed realistic sample scans and findings for quick testing"
        >
          {seedSuccess ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-purple-600" />
              <span>Demo Loaded</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-purple-600" />
              <span>{seeding ? 'Loading Demo...' : 'Seed Demo Data'}</span>
            </>
          )}
        </button>

        {/* New Scan Button */}
        {currentView !== 'new-scan' && (
          <button
            type="button"
            onClick={() => onNavigate('new-scan')}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl shadow-xs shadow-blue-200 transition-colors cursor-pointer"
          >
            <PlayCircle className="w-3.5 h-3.5" />
            <span>New Scan</span>
          </button>
        )}

        <div className="h-6 w-px bg-slate-200 mx-1" />
        <div className="flex items-center gap-2 pl-1">
          <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center font-bold text-xs text-blue-700">
            QA
          </div>
        </div>
      </div>
    </header>
  );
};
