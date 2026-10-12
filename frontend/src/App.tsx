import { useState } from 'react';
import './index.css';
import { Sidebar } from './components/Sidebar';
import { TopNav } from './components/TopNav';
import { NewScanView } from './views/NewScanView';
import { ReportsView } from './views/ReportsView';
import { SettingsView } from './views/SettingsView';

type ViewId = 'new-scan' | 'reports' | 'settings';

function App() {
  const [currentView, setCurrentView] = useState<ViewId>('new-scan');
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleNavigate = (view: string, scanId?: string) => {
    setCurrentView(view as ViewId);
    if (scanId) setActiveScanId(scanId);
  };

  const handleSelectScanFromReports = (scanId: string) => {
    setActiveScanId(scanId);
    setCurrentView('new-scan');
  };

  const renderContent = () => {
    switch (currentView) {
      case 'new-scan':
        return (
          <NewScanView
            key={`${activeScanId || 'none'}-${refreshKey}`}
            activeScanId={activeScanId}
            onScanChange={(scanId) => setActiveScanId(scanId)}
          />
        );
      case 'reports':
        return (
          <ReportsView
            key={`reports-${refreshKey}`}
            activeScanId={activeScanId}
            onSelectScan={handleSelectScanFromReports}
          />
        );
      case 'settings':
        return <SettingsView key={`settings-${refreshKey}`} />;
      default:
        return (
          <NewScanView
            activeScanId={activeScanId}
            onScanChange={(scanId) => setActiveScanId(scanId)}
          />
        );
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#F8FAFC]">
      {/* Sidebar - Only 3 views: New Scan, Reports, Settings */}
      <Sidebar
        currentView={currentView}
        onNavigate={handleNavigate}
        activeScanId={activeScanId}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopNav
          currentView={currentView}
          onNavigate={handleNavigate}
          onRefresh={() => setRefreshKey((k) => k + 1)}
        />

        {/* Scrollable Page Content */}
        <main className="flex-1 overflow-y-auto">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
