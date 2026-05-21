import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
  setPage: (page: 'dashboard' | 'rules' | 'upload' | 'analysis' | 'admin') => void;
  onLogout: () => void;
}

export const Layout: React.FC<LayoutProps> = ({ children, setPage, onLogout }) => {
  return (
    <div className="min-h-screen bg-slate-900 p-8 font-sans text-white">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12 flex justify-between items-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent pb-1">
            Race Agent
          </h1>
          <nav className="flex gap-4 items-center">
            <button
              onClick={() => setPage('admin')}
              className="text-slate-400 hover:text-white transition-colors bg-transparent border-none p-0 cursor-pointer"
            >
              Admin
            </button>
            <button
              onClick={() => setPage('dashboard')}
              className="text-slate-400 hover:text-white transition-colors bg-transparent border-none p-0 cursor-pointer"
            >
              Dashboard
            </button>
            <button
              onClick={() => setPage('analysis')}
              className="text-slate-400 hover:text-white transition-colors bg-transparent border-none p-0 cursor-pointer"
            >
              Analysis
            </button>
            <button
              onClick={() => setPage('rules')}
              className="text-slate-400 hover:text-white transition-colors bg-transparent border-none p-0 cursor-pointer"
            >
              Rules
            </button>
            <button
              onClick={() => setPage('upload')}
              className="text-slate-400 hover:text-white transition-colors bg-transparent border-none p-0 cursor-pointer"
            >
              Upload
            </button>
            <div className="h-6 w-px bg-white/10 mx-2" />
            <button
              onClick={onLogout}
              className="text-red-400 hover:text-red-300 transition-colors bg-transparent border-none p-0 cursor-pointer text-sm font-medium"
            >
              Logout
            </button>
          </nav>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
};
