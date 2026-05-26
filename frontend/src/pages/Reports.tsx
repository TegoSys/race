import { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import apiClient from '../lib/api';

interface Report {
  id: number;
  file_id: number;
  checked_at: string;
  total_violations: number;
  status: string;
  filename: string;
  venue: string;
  driver: string;
}

type PageCallback = (p: 'dashboard' | 'rules' | 'upload' | 'analysis' | 'admin' | 'diagnostics') => void;

export const Reports = ({ setPage }: { setPage: PageCallback }) => {
  const [reports, setReports] = useState<Report[]>([]);
  const [totalReports, setTotalReports] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [filenameFilter, setFilenameFilter] = useState<string>('');
  const [fileOptions, setFileOptions] = useState<string[]>([]);
  const [pageSize, setPageSize] = useState(() => {
    const saved = localStorage.getItem('reportsPageSize');
    return saved ? Number(saved) : 20;
  });
  const [currentPage, setCurrentPage] = useState(1);

  const fetchReports = () => {
    setIsLoading(true);
    const offset = (currentPage - 1) * pageSize;
    const params: Record<string, string | number> = { limit: pageSize, offset };
    if (statusFilter) params.status = statusFilter;
    if (filenameFilter) params.filename = filenameFilter;

    apiClient.get<{ reports: Report[]; total: number }>('/reports', { params })
      .then(res => {
        setReports(res.data.reports);
        setTotalReports(res.data.total);
      })
      .catch(e => console.error('Error fetching reports:', e))
      .finally(() => setIsLoading(false));
  };

  // Fetch reports when pagination or filters change
  useEffect(() => {
    fetchReports();
  }, [currentPage, pageSize, statusFilter, filenameFilter]);

  // Fetch file options for dropdown (once on mount)
  useEffect(() => {
    apiClient.get<{ reports: Report[]; total: number }>('/reports', { params: { limit: 500 } })
      .then(res => {
        const filenames = [...new Set(res.data.reports.map(r => r.filename))];
        setFileOptions(filenames);
      })
      .catch(e => console.error('Error fetching file options:', e));
  }, []);

  const handlePageChange = (newPage: number) => {
    const maxPage = Math.max(1, Math.ceil(totalReports / pageSize));
    if (newPage >= 1 && newPage <= maxPage) {
      setCurrentPage(newPage);
    }
  };

  const handleFilterChange = () => {
    setCurrentPage(1);
  };

  const handleReportClick = (reportId: number) => {
    window.dispatchEvent(new CustomEvent('selectReport', { detail: { summaryId: String(reportId) } }));
    setPage('diagnostics');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PASSED': return 'text-emerald-400';
      case 'WARNING': return 'text-yellow-400';
      case 'FAILED': return 'text-red-400';
      default: return 'text-slate-400';
    }
  };

  const maxPage = Math.max(1, Math.ceil(totalReports / pageSize));
  const startIdx = (currentPage - 1) * pageSize + 1;
  const endIdx = Math.min(currentPage * pageSize, totalReports);

  if (isLoading && reports.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-white font-medium">
        Loading Reports...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <h2 className="text-3xl font-bold text-white tracking-tight">Compliance Reports</h2>

      <Card variant="glass" className="p-6">
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex items-center gap-2">
            <label className="text-sm text-slate-400">Status:</label>
            <select
              value={statusFilter}
              onChange={e => { setStatusFilter(e.target.value); handleFilterChange(); }}
              className="bg-slate-800/50 border border-white/10 rounded-lg px-3 py-1 text-sm text-white outline-none focus:ring-2 ring-blue-500/50"
            >
              <option value="">All</option>
              <option value="PASSED">Passed</option>
              <option value="WARNING">Warning</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-slate-400">File:</label>
            <select
              value={filenameFilter}
              onChange={e => { setFilenameFilter(e.target.value); handleFilterChange(); }}
              className="bg-slate-800/50 border border-white/10 rounded-lg px-3 py-1 text-sm text-white outline-none focus:ring-2 ring-blue-500/50"
            >
              <option value="">All Files</option>
              {fileOptions.map(fn => (
                <option key={fn} value={fn}>{fn}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <label className="text-sm text-slate-400">Per page:</label>
            <select
              value={pageSize}
              onChange={e => {
                const size = Number(e.target.value);
                setPageSize(size);
                localStorage.setItem('reportsPageSize', String(size));
                setCurrentPage(1);
              }}
              className="bg-slate-800/50 border border-white/10 rounded-lg px-3 py-1 text-sm text-white outline-none focus:ring-2 ring-blue-500/50"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto border border-white/10 rounded-lg bg-slate-800/30">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-slate-400 uppercase text-xs font-bold">
              <tr>
                <th className="p-3 border-b border-white/10">Date</th>
                <th className="p-3 border-b border-white/10">Filename</th>
                <th className="p-3 border-b border-white/10">Venue</th>
                <th className="p-3 border-b border-white/10">Driver</th>
                <th className="p-3 border-b border-white/10">Status</th>
                <th className="p-3 border-b border-white/10">Violations</th>
              </tr>
            </thead>
            <tbody className="text-slate-300">
              {reports.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center italic text-slate-500">
                    No reports found.
                  </td>
                </tr>
              ) : (
                reports.map(report => (
                  <tr
                    key={report.id}
                    onClick={() => handleReportClick(report.id)}
                    className="hover:bg-white/5 transition-colors cursor-pointer border-b border-white/5"
                  >
                    <td className="p-3 font-mono text-xs">
                       {new Date(report.checked_at).toLocaleString()}
                    </td>
                    <td className="p-3 font-medium text-white">{report.filename}</td>
                    <td className="p-3">{report.venue || '—'}</td>
                    <td className="p-3">{report.driver || '—'}</td>
                    <td className={`p-3 font-bold ${getStatusColor(report.status)}`}>
                       {report.status}
                    </td>
                    <td className="p-3 font-mono">{report.total_violations}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-3">
          <div className="text-slate-400 text-xs">
            {totalReports > 0
              ? `Showing ${startIdx}–${endIdx} of ${totalReports} reports`
              : `No reports`}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="px-3 py-1 text-xs text-slate-300 bg-slate-800/50 border border-white/10 rounded-lg hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <span className="text-slate-400 text-xs px-2">
              Page {currentPage} of {maxPage}
            </span>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= maxPage}
              className="px-3 py-1 text-xs text-slate-300 bg-slate-800/50 border border-white/10 rounded-lg hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
};
