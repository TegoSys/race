import { useState, useEffect } from 'react';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Upload } from './pages/Upload';
import { Analysis } from './pages/Analysis';
import { Admin } from './pages/Admin';
import { Rules } from './pages/Rules';
import { Reports } from './pages/Reports';
import { DiagnosticsView } from './pages/DiagnosticsView';
import Login from './pages/Login';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const { isAuthenticated, logout } = useAuth();
  const [page, setPage] = useState<'dashboard' | 'rules' | 'reports' | 'upload' | 'analysis' | 'admin' | 'diagnostics'>('dashboard');
  const [navCounter, setNavCounter] = useState(0);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [selectedSummaryId, setSelectedSummaryId] = useState<string | null>(null);
  const [showLogin, setShowLogin] = useState(!isAuthenticated);

  // Listen for report selection events
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { summaryId: string };
      setSelectedSummaryId(detail.summaryId);
      setSelectedFileId(null);
    };
    window.addEventListener('selectReport', handler);
    return () => window.removeEventListener('selectReport', handler);
  }, []);

  const navigate = (p: 'dashboard' | 'rules' | 'reports' | 'upload' | 'analysis' | 'admin' | 'diagnostics') => {
    setNavCounter(k => k + 1);
    setPage(p);
    // Clear selection when not navigating to diagnostics
    if (p !== 'diagnostics') {
      setSelectedSummaryId(null);
    }
  };

  if (showLogin || !isAuthenticated) {
    return <Login onLoginSuccess={() => setShowLogin(false)} />;
  }

  return (
    <Layout setPage={navigate} onLogout={() => {
      logout();
      setShowLogin(true);
    }}>
      {page === 'dashboard' ? <Dashboard key={navCounter} /> :
       page === 'rules' ? <Rules key={navCounter} /> :
       page === 'reports' ? <Reports key={navCounter} setPage={navigate} /> :
       page === 'upload' ? <Upload key={navCounter} /> :
       page === 'analysis' ? <Analysis key={navCounter} setPage={navigate} setSelectedFileId={setSelectedFileId} /> :
       page === 'diagnostics' ? <DiagnosticsView key={navCounter} fileId={selectedFileId} summaryId={selectedSummaryId} /> :
       <Admin key={navCounter} />}

      <div className="fixed bottom-8 right-8 flex gap-4 hidden">
        <button
          onClick={() => navigate('dashboard')}
          className={`px-4 py-2 rounded-lg transition-all ${page === 'dashboard' ? 'bg-white/20 text-white' : 'text-slate-400 hover:text-white'}`}
        >
          Dashboard
        </button>
        <button
          onClick={() => navigate('analysis')}
          className={`px-4 py-2 rounded-lg transition-all ${page === 'analysis' ? 'bg-white/20 text-white' : 'text-slate-400 hover:text-white'}`}
        >
          Analysis
        </button>
        <button
          onClick={() => navigate('upload')}
          className={`px-4 py-2 rounded-lg transition-all ${page === 'upload' ? 'bg-white/20 text-white' : 'text-slate-400 hover:text-white'}`}
        >
          Upload
        </button>
      </div>
    </Layout>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
