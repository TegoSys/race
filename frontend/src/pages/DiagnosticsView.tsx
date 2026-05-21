import React, { useEffect, useMemo, useState } from 'react';
import { Card } from '../components/ui/Card';
import { AlertCircle, CheckCircle2, AlertTriangle, Download } from 'lucide-react';
import apiClient from '../lib/api';

interface Violation {
  rule_id: string;
  severity: string;
  description: string;
  timestamp: number;
  value: number;
  context_json: any;
}

interface Summary {
  id: number;
  file_id: number;
  checked_at: string;
  total_violations: number;
  status: string;
  summary_json: any;
}

interface DiagnosticsData {
  summary: Summary;
  violations: Violation[];
}

export const DiagnosticsView = ({ fileId }: { fileId: string | null }) => {
  const [data, setData] = useState<DiagnosticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState<number | 'All'>(5);

  useEffect(() => {
    if (!fileId) return;
    setIsLoading(true);
    setError(null);
    const controller = new AbortController();
    apiClient.get<DiagnosticsData>(`/files/${fileId}/rules`, { signal: controller.signal })
      .then(res => {
        setData(res.data);
        setIsLoading(false);
      })
      .catch(err => {
        if (!controller.signal.aborted) {
          setError(err.message || 'Unknown error');
          setIsLoading(false);
        }
      });
    return () => controller.abort();
  }, [fileId]);

  // Hooks MUST be before any early returns (React Rules of Hooks)
  const safeData = data || { summary: {} as Summary, violations: [] };
  const violations = safeData.violations || [];

  const paginatedViolations = useMemo(() => {
    const grouped: Record<string, Violation[]> = {};
    violations.forEach(v => {
      if (!grouped[v.rule_id]) grouped[v.rule_id] = [];
      grouped[v.rule_id].push(v);
    });
    const result: Violation[] = [];
    Object.values(grouped).forEach(group => {
      result.push(...(pageSize === 'All' ? group : group.slice(0, pageSize)));
    });
    return result;
  }, [violations, pageSize]);

  if (!fileId) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500 italic">
        Please select a file to view diagnostics.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center text-white font-medium">
        Loading Diagnostics...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-full flex items-center justify-center text-red-400 italic">
        Error loading diagnostics: {error || 'Unknown error'}
      </div>
    );
  }

  const { summary } = data;

  const ruleBreakdown = (typeof summary.summary_json === 'string'
    ? JSON.parse(summary.summary_json)
    : summary.summary_json) || {};

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PASSED': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
      case 'WARNING': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
      case 'FAILED': return 'text-red-400 bg-red-400/10 border-red-400/20';
      default: return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
    }
  };

  const getSeverityColor = (severity: string) => {
    return severity.toLowerCase() === 'critical' ? 'text-red-400' : 'text-yellow-400';
  };

  const handleDownloadMarkdown = () => {
    const ts = new Date(summary.checked_at).toISOString().replace(/[:T]/g, '-').slice(0, 15);
    const filename = `diagnostic_${ts}.md`;

    let md = '# Compliance Diagnostics Report\n\n';
    md += `**File ID:** #${summary.file_id}  `;
    md += `**Checked at:** ${new Date(summary.checked_at).toLocaleString()}\n\n`;

    md += '## Summary\n\n';
    md += '| Status | Total Violations |\n';
    md += '|--------|------------------|\n';
    md += `| ${summary.status} | ${summary.total_violations} |\n\n`;

    md += '## Rule Breakdown\n\n';
    md += '| Rule | Status | Violations |\n';
    md += '|------|--------|------------|\n';
    Object.entries(ruleBreakdown).forEach(([_id, data]) => {
      const r = data as any;
      md += `| ${r.name || '-'} | ${r.status} | ${r.count ?? 0} |\n`;
    });

    md += '\n## Detailed Violations\n\n';
    md += '| Rule | Severity | Description | Value | Timestamp |\n';
    md += '|------|----------|-------------|-------|-----------|\n';
    violations.forEach(v => {
      const val = v.value != null ? v.value.toFixed(4) : '—';
      const t = v.timestamp != null ? `${v.timestamp.toFixed(2)}s` : '—';
      md += `| ${v.rule_id} | ${v.severity} | ${v.description} | ${val} | ${t} |\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold text-white tracking-tight">Compliance Diagnostics</h2>
        <div className="flex items-center gap-4">
          <button
            onClick={handleDownloadMarkdown}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm font-medium bg-transparent border-none p-0 cursor-pointer"
          >
            <Download size={16} />
            Download Report
          </button>
          <div className="text-slate-400 text-sm">
            Checked at: {new Date(summary.checked_at).toLocaleString()}
          </div>
        </div>
      </div>

      {/* Global Summary Card */}
      <Card variant="glass" className={`p-8 border-l-4 ${getStatusColor(summary.status).split(' ')[2]} transition-all`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              {summary.status === 'PASSED' && <CheckCircle2 className="text-emerald-400" size={32} />}
              {summary.status === 'WARNING' && <AlertTriangle className="text-yellow-400" size={32} />}
              {summary.status === 'FAILED' && <AlertCircle className="text-red-400" size={32} />}
              <h3 className={`text-4xl font-black uppercase tracking-widest ${getStatusColor(summary.status).split(' ')[0]}`}>
                {summary.status}
              </h3>
            </div>
            <p className="text-slate-400 text-lg">
              {summary.status === 'PASSED'
                ? 'System is fully compliant with all telemetry rules.'
                : `Detected ${summary.total_violations} violations across the dataset.`}
            </p>
          </div>
          <div className="flex gap-8">
            <div className="text-center">
              <div className="text-slate-400 text-xs uppercase font-bold mb-1">Total Violations</div>
              <div className="text-3xl font-mono font-bold text-white">{summary.total_violations}</div>
            </div>
            <div className="text-center">
              <div className="text-slate-400 text-xs uppercase font-bold mb-1">File ID</div>
              <div className="text-3xl font-mono font-bold text-white">#{summary.file_id}</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Rule Breakdown Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {Object.entries(ruleBreakdown).map(([ruleId, ruleDataRaw]) => {
          const ruleData = ruleDataRaw as any;
          return (
            <Card key={ruleId} variant="glass" className="p-4 flex flex-col items-center text-center space-y-3 border-t-2 border-transparent hover:border-white/20 transition-all">
              <div className="text-xs text-slate-400 uppercase font-bold tracking-wider">{ruleData.name}</div>
              <div className={`px-3 py-1 rounded-full text-xs font-bold ${ruleData.status === 'PASS' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                {ruleData.status}
              </div>
              <div className="text-2xl font-mono font-bold text-white">{ruleData.count}</div>
            </Card>
          );
        })}
      </div>

      {/* Detailed Violations Table */}
      <Card variant="glass" className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-white flex items-center gap-2">
            <AlertCircle size={20} className="text-blue-400" />
            Detailed Violation Log
          </h3>
          <div className="flex items-center gap-3">
            <span className="text-slate-400 text-xs">
              Showing {paginatedViolations.length} of {violations.length}
            </span>
            <span className="text-slate-500 text-xs">per rule:</span>
            <select
              value={pageSize}
              onChange={e => setPageSize(e.target.value as number | 'All')}
              className="bg-white/10 border border-white/10 rounded-lg px-2 py-1 text-white text-xs font-mono outline-none focus:ring-2 ring-blue-500/50"
            >
              <option value={5} style={{ background: '#1e293b', color: '#fff' }}>5</option>
              <option value={10} style={{ background: '#1e293b', color: '#fff' }}>10</option>
              <option value={25} style={{ background: '#1e293b', color: '#fff' }}>25</option>
              <option value={50} style={{ background: '#1e293b', color: '#fff' }}>50</option>
              <option value="All" style={{ background: '#1e293b', color: '#fff' }}>All</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto border border-white/10 rounded-xl bg-slate-900/40">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-slate-400 uppercase text-xs font-bold">
              <tr>
                <th className="p-4 border-b border-white/10">Rule</th>
                <th className="p-4 border-b border-white/10">Severity</th>
                <th className="p-4 border-b border-white/10">Description</th>
                <th className="p-4 border-b border-white/10">Value</th>
                <th className="p-4 border-b border-white/10">Timestamp</th>
              </tr>
            </thead>
            <tbody className="text-slate-300">
              {paginatedViolations.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center italic text-slate-500">
                    No detailed violations recorded.
                  </td>
                </tr>
              ) : (
                paginatedViolations.map((v, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors border-b border-white/5">
                    <td className="p-4 font-medium text-white">{v.rule_id}</td>
                    <td className={`p-4 font-bold ${getSeverityColor(v.severity)}`}>
                      {v.severity}
                    </td>
                    <td className="p-4">{v.description}</td>
                    <td className="p-4 font-mono text-blue-400">{v.value != null ? v.value.toFixed(4) : '—'}</td>
                    <td className="p-4 font-mono text-xs">{v.timestamp != null ? `${v.timestamp.toFixed(2)}s` : '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};