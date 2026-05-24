import React, { useState, useEffect, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import apiClient from '../lib/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar
} from 'recharts';
import domtoImage from 'dom-to-image-more';
import { Star, Download, X } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { TrackPlot } from '../components/TrackPlot';
import { API_BASE_URL } from '../config';

const API_BASE = API_BASE_URL;

const SummaryView = ({ summaryData, fileId }: { summaryData: any, fileId: string }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [favoriteChannels, setFavoriteChannels] = useState<string[]>(() => {
    const saved = localStorage.getItem('favoriteChannels');
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    localStorage.setItem('favoriteChannels', JSON.stringify(favoriteChannels));
  }, [favoriteChannels]);

  if (!summaryData) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500 italic border-2 border-dashed border-white/10 rounded-2xl min-h-[600px]">
        No summary data available for this file.
      </div>
    );
  }

  const { metadata, stats, correlations } = summaryData;
  const parsedMeta = typeof metadata === 'string' ? JSON.parse(metadata) : metadata;

  const toggleFavorite = (channel: string) => {
    setFavoriteChannels(prev =>
      prev.includes(channel) ? prev.filter(c => c !== channel) : [...prev, channel]
    );
  };

  const shiftedStats = (stats || []).map((s: any, idx: number) => ({
   ...s,
   unit: stats[idx + 1]?.unit ?? s.unit,
  }));

  const filteredStats = shiftedStats?.filter((s: any) => {
    const matchesSearch = s.channel_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFavorite = !showFavoritesOnly || favoriteChannels.includes(s.channel_name);
    return matchesSearch && matchesFavorite;
  }) || [];

  return (
    <div className="space-y-6">
      {!summaryData ? (
        <div className="h-full flex items-center justify-center text-slate-500 italic border-2 border-dashed border-white/10 rounded-2xl min-h-[600px]">
          No summary data available for this file.
        </div>
      ) : (
        <>
          {/* Metadata Grid */}
          <Card variant="glass" className="p-6">
            <h3 className="text-lg font-medium text-white mb-4">File Metadata</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(parsedMeta || {})
                .filter(([key]) => !key.toLowerCase().includes('beacon markers'))
                .map(([key, value]) => (
                <div key={key} className="p-3 bg-white/5 rounded-lg border border-white/10">
                  <div className="text-xs text-slate-400 uppercase font-semibold">{key.replace('_', ' ')}</div>
                  <div className="text-white font-medium">{String(value)}</div>
                </div>
              ))}
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-6">
            {/* Stats Table */}
            <Card variant="glass" className="p-6">
              <div className="flex flex-wrap flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
                <h3 className="text-lg font-medium text-white">Channel Statistics</h3>
                <div className="flex items-center gap-3 w-full sm:w-auto">
                  <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showFavoritesOnly}
                      onChange={(e) => setShowFavoritesOnly(e.target.checked)}
                      className="accent-blue-500"
                    />
                    Favorites Only
                  </label>
                  <input
                    type="text"
                    placeholder="Filter channels..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-slate-800/50 border border-white/10 rounded-lg px-3 py-1 text-sm text-white outline-none focus:ring-2 ring-blue-500/50 w-full sm:w-48"
                  />
                </div>
              </div>
              <div className="overflow-x-auto max-h-96 border border-white/10 rounded-lg bg-slate-800/30">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="sticky top-0 bg-slate-900 text-white">
                    <tr>
                      <th className="p-2 border-b border-white/10 w-8"></th>
                      <th className="p-2 border-b border-white/10">Channel</th>
                      <th className="p-2 border-b border-white/10">Unit</th>
                      <th className="p-2 border-b border-white/10">Min</th>
                      <th className="p-2 border-b border-white/10">Max</th>
                      <th className="p-2 border-b border-white/10">Avg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredStats.map((s: any, i) => (
                      <tr key={i} className="hover:bg-white/5 transition-colors">
                        <td className="p-2 border-b border-white/5 text-center">
                          <button
                            onClick={() => toggleFavorite(s.channel_name)}
                            className={`transition-colors ${favoriteChannels.includes(s.channel_name) ? 'text-yellow-400' : 'text-slate-500 hover:text-slate-300'}`}
                          >
                            <Star size={16} fill={favoriteChannels.includes(s.channel_name) ? 'currentColor' : 'none'} />
                          </button>
                        </td>
                        <td className="p-2 border-b border-white/5 font-medium text-white">{s.channel_name}</td>
                        <td className="p-2 border-b border-white/5">{s.unit}</td>
                        <td className="p-2 border-b border-white/5 font-mono">{s.min_val?.toFixed(3)}</td>
                        <td className="p-2 border-b border-white/5 font-mono">{s.max_val?.toFixed(3)}</td>
                        <td className="p-2 border-b border-white/5 font-mono">{s.avg_val?.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Correlation Insights */}
            <Card variant="glass" className="p-6">
              <h3 className="text-lg font-medium text-white mb-4">Correlation Insights</h3>
              <div className="space-y-3">
                {correlations && Object.entries(correlations).length > 0 ? (
                  Object.entries(correlations).map(([pair, value]: [string, any]) => {
                    const val = typeof value === 'string' ? parseFloat(value) : value;
                    const strength = Math.abs(val);
                    let color = 'text-slate-400';
                    if (strength > 0.7) color = 'text-emerald-400';
                    else if (strength > 0.4) color = 'text-blue-400';

                    return (
                      <div key={pair} className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10">
                        <span className="text-sm text-slate-300">{pair}</span>
                        <div className="flex items-center gap-3">
                          <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${color.replace('text', 'bg')}`}
                              style={{ width: `${strength * 100}%` }}
                            />
                          </div>
                          <span className={`text-sm font-mono font-bold ${color}`}>
                            {val.toFixed(3)}
                          </span>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-slate-500 italic text-sm">No correlation data available.</div>
                )}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
};

export const Analysis = ({ setPage, setSelectedFileId }: { setPage: (p: any) => void, setSelectedFileId: (id: string | null) => void }) => {
  const [files, setFiles] = useState<{ id: number, filename: string }[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [availableColumns, setAvailableColumns] = useState<string[]>([]);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [downsampleFactor, setDownsampleFactor] = useState<number>(100);
  const [data, setData] = useState<any[]>([]);
  const [summaryData, setSummaryData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'analysis' | 'summary' | 'trackPlot'>('analysis');
  const [loading, setLoading] = useState(false);

  const { mutateAsync: runDiagnosticsAsync, isPending: isDiagnosticsPending } = useMutation({
    mutationFn: async (payload: { id: string, factor: number }) => {
      const res = await apiClient.post(`/files/${payload.id}/run-checks`, { downsample_factor: payload.factor });
      return res.data;
    }
  });

  const handleCheckDiagnostics = async () => {
    if (!selectedFile) return;
    try {
      await runDiagnosticsAsync({ id: selectedFile, factor: downsampleFactor });
      setSelectedFileId(selectedFile);
      setPage('diagnostics');
    } catch (e) {
      console.error('Diagnostics failed:', e);
    }
  };

  // Export state
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSettings, setExportSettings] = useState({
    filename: '',
    plotType: 'timeSeries', // 'timeSeries' or 'histograms'
  });

  const dashboardRef = useRef<HTMLDivElement>(null);
  const timeSeriesRef = useRef<HTMLDivElement>(null);
  const histogramsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchFiles();
  }, []);

  useEffect(() => {
    if (selectedFile) {
      fetchColumns(selectedFile);
      fetchSummary(selectedFile);
    } else {
      setSummaryData(null);
    }
  }, [selectedFile]);

  useEffect(() => {
    if (selectedFile && selectedColumns.length > 0) {
      fetchData();
    }
  }, [selectedFile, selectedColumns, downsampleFactor]);

  const fetchFiles = async () => {
    try {
      const res = await apiClient.get('/files');
      setFiles(res.data);
    } catch (e) {
      console.error('Error fetching files', e);
    }
  };

  const fetchColumns = async (fileId: string) => {
    try {
      const res = await apiClient.get(`/files/${fileId}/columns`);
      setAvailableColumns(res.data);
    } catch (e) {
      console.error('Error fetching columns', e);
    }
  };

  const fetchSummary = async (fileId: string) => {
    try {
      const res = await apiClient.get(`/files/${fileId}/summary`);
      setSummaryData(res.data);
    } catch (e) {
      console.error('Error fetching summary', e);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const cols = selectedColumns.join(',');
      const res = await apiClient.get('/files/data', {
        params: {
          file_id: selectedFile,
          columns: cols,
          downsample_factor: downsampleFactor
        }
      });
      setData(res.data);
    } catch (e) {
      console.error('Error fetching data', e);
    } finally {
      setLoading(false);
    }
  };

  const toggleColumn = (col: string) => {
    setSelectedColumns(prev =>
      prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]
    );
  };

  const clearAllColumns = () => setSelectedColumns([]);

  const savePlot = () => {
    setExportSettings({
      filename: `race-analysis-${selectedFile || 'export'}`,
      plotType: 'timeSeries'
    });
    setIsExportModalOpen(true);
  };

  const executeExport = async () => {
    setIsExporting(true);
    try {
      const targetElement = exportSettings.plotType === 'timeSeries'
        ? timeSeriesRef.current
        : histogramsRef.current;

      if (!targetElement) {
        throw new Error('Target element for export not found');
      }

      // dom-to-image-more uses browser rendering via SVG foreignObject,
      // which handles modern CSS like oklch() correctly.
      const image = await domtoImage.toPng(targetElement, {
        backgroundColor: '#0f172a',
        width: targetElement.offsetWidth,
        height: targetElement.offsetHeight,
      });

      const link = document.createElement('a');
      link.download = `${exportSettings.filename}.png`;
      link.href = image;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setIsExportModalOpen(false);
    } catch (e) {
      console.error('Export failed', e);
      alert(`Export failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Helper to calculate histogram bins
  const generateHistogramData = (column: string) => {
    if (data.length === 0) return [];
    const values = data.map(d => d[column]).filter(v => typeof v === 'number');
    if (values.length === 0) return [];

    const min = Math.min(...values);
    const max = Math.max(...values);
    const binSize = (max - min) / 30;
    const bins = new Array(30).fill(0);

    values.forEach(v => {
      const binIdx = Math.min(Math.floor((v - min) / binSize), 29);
      bins[binIdx]++;
    });

    return bins.map((count, i) => ({
      bin: `${(min + i * binSize).toFixed(2)}`,
      count
    }));
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <Card variant="glass" className="p-6 space-y-6 self-start">
          <h2 className="text-xl font-semibold text-white">Analysis Setup</h2>

          <div className="space-y-2">
            <label className="text-sm text-slate-400">Select File</label>
            <select
              value={selectedFile}
              onChange={(e) => { setSelectedFile(e.target.value); setSelectedColumns([]); }}
              className="w-full bg-slate-800/50 border border-white/10 rounded-lg p-2 text-white outline-none focus:ring-2 ring-blue-500/50"
            >
              <option value="">-- Choose a file --</option>
              {files.map(f => <option key={f.id} value={f.id}>{f.filename}</option>)}
            </select>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm text-emerald-400">Select Channels</label>
              <Button
                variant="outline"
                size="sm"
                onClick={clearAllColumns}
                disabled={selectedColumns.length === 0}
              >
                Reset
              </Button>
            </div>
            <div className="h-120 overflow-y-auto border border-white/10 rounded-lg p-2 space-y-1 bg-slate-800/30">
              {availableColumns.map(col => (
                <label key={col} className="flex items-center gap-2 p-1 hover:bg-white/5 rounded cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selectedColumns.includes(col)}
                    onChange={() => toggleColumn(col)}
                    className="accent-blue-500"
                  />
                  <span className={`text-sm ${selectedColumns.includes(col) ? 'text-white' : 'text-slate-400'} group-hover:text-slate-200`}>
                    {col}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm text-slate-400">Downsample Factor</label>
              <span className="text-xs text-blue-400">{downsampleFactor}x</span>
            </div>
            <input
              type="range"
              min="1"
              max="200"
              value={downsampleFactor}
              onChange={(e) => setDownsampleFactor(parseInt(e.target.value))}
              className="w-full accent-blue-500"
            />
          </div>

          <div className="flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={savePlot}
              disabled={data.length === 0}
            >
              Save Plots
            </Button>
          </div>
        </Card>

        {/* Export Modal */}
        {isExportModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <Card variant="glass" className="p-6 w-full max-w-md shadow-2xl border-blue-500/30">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-semibold text-white">Export Plots</h3>
                <button onClick={() => setIsExportModalOpen(false)} className="text-slate-400 hover:text-white">
                  <X size={20} />
                </button>
              </div>

              <div className="space-y-6">
                <div className="space-y-3">
                  <label className="text-sm text-slate-400">Select Plots to Export</label>
                  <div className="flex flex-col gap-3">
                    <label className="flex items-center gap-3 p-3 bg-white/5 rounded-lg border border-white/10 cursor-pointer hover:bg-white/10 transition-colors">
                      <input
                        type="radio"
                        name="plotType"
                        checked={exportSettings.plotType === 'timeSeries'}
                        onChange={() => setExportSettings(prev => ({ ...prev, plotType: 'timeSeries' }))}
                        className="accent-blue-500 w-4 h-4"
                      />
                      <span className="text-sm text-slate-300">Time Series Plot</span>
                    </label>
                    <label className="flex items-center gap-3 p-3 bg-white/5 rounded-lg border border-white/10 cursor-pointer hover:bg-white/10 transition-colors">
                      <input
                        type="radio"
                        name="plotType"
                        checked={exportSettings.plotType === 'histograms'}
                        onChange={() => setExportSettings(prev => ({ ...prev, plotType: 'histograms' }))}
                        className="accent-blue-500 w-4 h-4"
                      />
                      <span className="text-sm text-slate-300">Distribution Histograms</span>
                    </label>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-slate-400">Filename</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={exportSettings.filename}
                      onChange={(e) => setExportSettings(prev => ({ ...prev, filename: e.target.value }))}
                      className="w-full bg-slate-800/50 border border-white/10 rounded-lg p-2 text-white outline-none focus:ring-2 ring-blue-500/50 text-sm"
                      placeholder="Enter filename..."
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">.png</span>
                  </div>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    onClick={() => setIsExportModalOpen(false)}
                    className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-sm font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={executeExport}
                    disabled={!exportSettings.filename || isExporting}
                    className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2"
                  >
                    {isExporting ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Exporting...
                      </>
                    ) : (
                      <>
                        <Download size={16} />
                        Download
                      </>
                    )}
                  </button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Main Dashboard */}
        <div ref={dashboardRef} className="md:col-span-2 space-y-6">
          <div className="flex gap-2 p-1 bg-slate-800/50 border border-white/10 rounded-xl w-fit">
            <button
              onClick={() => setActiveTab('analysis')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'analysis'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              Chart Analysis
            </button>
            <button
              onClick={() => setActiveTab('summary')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'summary'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              File Summary
            </button>
            <button
              onClick={() => setActiveTab('trackPlot')}
              disabled={!selectedFile || !availableColumns.includes('GPS Latitude') || !availableColumns.includes('GPS Longitude')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'trackPlot'
                ? 'bg-blue-600 text-white shadow-lg'
                : (!selectedFile || !availableColumns.includes('GPS Latitude') || !availableColumns.includes('GPS Longitude'))
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-white/10 text-white hover:bg-white/20 shadow-sm border border-white/10'
              }`}
            >
              Track Plot
            </button>
            <button
              onClick={handleCheckDiagnostics}
              disabled={!selectedFile || isDiagnosticsPending}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                !selectedFile || isDiagnosticsPending
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-white/10 text-white hover:bg-white/20 shadow-sm border border-white/10'
              }`}
            >
              {isDiagnosticsPending && <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
              {isDiagnosticsPending ? 'Running...' : 'Check Diagnostics'}
            </button>
          </div>

          {loading && (
            <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm z-10 flex items-center justify-center text-white font-medium">
              Loading Data...
            </div>
          )}

          {!selectedFile ? (
            <div className="h-full flex items-center justify-center text-slate-500 italic border-2 border-dashed border-white/10 rounded-2xl min-h-[600px]">
              Please select a file to begin analysis.
            </div>
          ) : (
            <>
              {activeTab === 'analysis' && (
                <>
                  {selectedColumns.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-slate-500 italic border-2 border-dashed border-white/10 rounded-2xl min-h-[600px]">
                      Please select at least one column to begin analysis.
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Time Series Plot */}
                      <Card ref={timeSeriesRef} variant="glass" className="p-6">
                        <h3 className="text-lg font-medium text-white mb-4">Time Series</h3>
                        <div className="h-80 w-full">
                          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                            <LineChart data={data}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                              <XAxis
  dataKey="index"
  stroke="#94a3b8"
  fontSize={10}
  tickFormatter={(val) => `S${val}`}
/>
                              <YAxis stroke="#94a3b8" fontSize={12} />
                              <Tooltip
                                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }}
                                itemStyle={{ color: '#fff' }}
                              />
                              <Legend />
                              {selectedColumns.map((col, idx) => (
                                <Line
                                  key={col}
                                  type="monotone"
                                  dataKey={col}
                                  stroke={['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'][idx % 5]}
                                  dot={false}
                                  strokeWidth={2}
                                />
                              ))}
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </Card>

                      {/* Histograms */}
                      <div ref={histogramsRef} className="grid grid-cols-1 gap-6">
                        {selectedColumns.map(col => (
                          <Card key={col} variant="glass" className="p-6">
                            <h3 className="text-md font-medium text-white mb-4">{col} Distribution</h3>
                            <div className="h-64 w-full">
                              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                                <BarChart data={generateHistogramData(col)}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                                  <XAxis dataKey="bin" stroke="#94a3b8" fontSize={10} />
                                  <YAxis stroke="#94a3b8" fontSize={12} />
                                  <Tooltip
                                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }}
                                    itemStyle={{ color: '#fff' }}
                                  />
                                  <Bar dataKey="count" fill="#3b82f6" />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          </Card>
                        ))}
                      </div>

                      {/* Data Table */}
                      <Card variant="glass" className="p-6">
                        <h3 className="text-lg font-medium text-white mb-4">Data View</h3>
                        <div className="overflow-x-auto max-h-96 border border-white/10 rounded-lg bg-slate-800/30">
                          <table className="w-full text-left text-sm text-slate-300">
                            <thead className="sticky top-0 bg-slate-900 text-white">
                              <tr>
                                <th className="p-2 border-b border-white/10">Row</th>
                                {selectedColumns.map(col => (
                                  <th key={col} className="p-2 border-b border-white/10">{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {data.map((row, i) => (
                                <tr key={i} className="hover:bg-white/5 transition-colors">
                                  <td className="p-2 border-b border-white/5 font-mono text-xs">{i}</td>
                                  {selectedColumns.map(col => (
                                    <td key={col} className="p-2 border-b border-white/5 font-mono text-xs">
                                      {typeof row[col] === 'number' ? row[col].toFixed(4) : row[col]}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </Card>
                    </div>
                  )}
                </>
              )}
              {activeTab === 'summary' && (
                <SummaryView
                  summaryData={summaryData}
                  fileId={selectedFile}
                  onRunDiagnostics={async (id) => {
                    setSelectedFileId(id);
                    setPage('diagnostics');
                  }}
                />
              )}
              {activeTab === 'trackPlot' && selectedFile && (
                <TrackPlot fileId={selectedFile} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
