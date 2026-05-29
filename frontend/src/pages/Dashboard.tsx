import React, { useState, useEffect } from 'react';
import apiClient from '../lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

const cleanMetadata = (value: string): string =>
  String(value)
    .trim()
    .replace(/"/g, '')
    .replace(/,+/g, ',')
    .replace(/,$/, '')
    .replace(/\b\w/g, c => c.toUpperCase());

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<{
    total_files: number;
    active_drivers: number;
    active_cars: number;
    total_races: number;
  } | null>(null);
  const [files, setFiles] = useState<{ id: number, filename: string }[]>([]);
  const [selectedFileId, setSelectedFileId] = useState(() => localStorage.getItem('dashboardSelectedFile') || '');
  const [selectedFileSummary, setSelectedFileSummary] = useState<any>(null);
  const [selectedFileLaps, setSelectedFileLaps] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Fetch summary if a file was persisted from a previous visit
  useEffect(() => {
    if (selectedFileId) {
      handleFileChange(selectedFileId);
    }
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, filesRes] = await Promise.all([
        apiClient.get('/stats'),
        apiClient.get('/files')
      ]);
      setStats(statsRes.data);
      setFiles(filesRes.data);
    } catch (e) {
      console.error('Error fetching dashboard data', e);
    }
  };

  const handleFileChange = async (fileId: string) => {
    setSelectedFileId(fileId);
    localStorage.setItem('dashboardSelectedFile', fileId);
    if (!fileId) {
      setSelectedFileSummary(null);
      setSelectedFileLaps(null);
      return;
    }

    setLoading(true);
    try {
      const [summaryRes, lapsRes] = await Promise.all([
        apiClient.get(`/files/${fileId}/summary`),
        apiClient.get(`/files/${fileId}/laps`)
      ]);
      setSelectedFileSummary(summaryRes.data);
      setSelectedFileLaps(lapsRes.data);
    } catch (e) {
      console.error('Error fetching file data', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card variant="glass" className="col-span-2">
        <CardHeader>
          <CardTitle>Race Overview</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center gap-4">
            <label className="text-sm text-slate-400">Select File:</label>
            <select
              value={selectedFileId}
              onChange={(e) => handleFileChange(e.target.value)}
              className="bg-slate-800/50 border border-white/10 rounded-lg p-2 text-white outline-none focus:ring-2 ring-blue-500/50 text-sm"
            >
              <option value="">-- Choose a file --</option>
              {files.map(f => <option key={f.id} value={f.id}>{f.filename}</option>)}
            </select>
          </div>

          {!selectedFileId ? (
            <div className="h-64 bg-slate-800/50 rounded-xl border border-slate-700 flex items-center justify-center">
              <span className="text-slate-500 italic">Select a race file to see detailed analytics.</span>
            </div>
          ) : loading ? (
            <div className="h-64 bg-slate-800/50 rounded-xl border border-slate-700 flex items-center justify-center">
              <span className="text-blue-400 animate-pulse">Loading file insights...</span>
            </div>
          ) : selectedFileSummary ? (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Card variant="glass" className="p-4 bg-white/5">
                <h4 className="text-sm font-medium text-slate-400 mb-2">File Metadata</h4>
                <div className="space-y-1 text-sm">
                  {Object.entries(typeof selectedFileSummary.metadata === 'string'
                    ? JSON.parse(selectedFileSummary.metadata)
                    : selectedFileSummary.metadata || {}
                  ).map(([key, value]) => (
                    <div key={key} className="grid grid-cols-[auto_1fr] gap-2">
                      <span className="text-slate-500 text-right">{key.replace('_', ' ')}:</span>
                      <span className="text-white font-mono">{cleanMetadata(String(value))}</span>
                    </div>
                  ))}
                </div>
              </Card>
              <Card variant="glass" className="p-4 bg-white/5">
                <h4 className="text-sm font-medium text-slate-400 mb-2">Top Correlations</h4>
                <div className="space-y-2">
                  {Object.entries(selectedFileSummary.correlations || {})
                    .sort(([, a], [, b]) => Math.abs(b as number) - Math.abs(a as number))
                    .slice(0, 3)
                    .map(([pair, val]) => (
                      <div key={pair} className="flex justify-between items-center text-xs gap-3">
                        <span className="text-slate-300">{pair}</span>
                        <span className={`font-mono font-bold ${Math.abs(val as number) > 0.7 ? 'text-emerald-400' : 'text-blue-400'}`}>
                          {Number(val).toFixed(3)}
                        </span>
                      </div>
                    ))
                  }
                </div>
              </Card>
            </div>

            {/* Lap Performance Section */}
            {selectedFileLaps && selectedFileLaps.supported && selectedFileLaps.session ? (
              <Card variant="glass" className="p-6">
                <h3 className="text-lg font-medium text-white mb-4">Lap Performance</h3>
                {/* Session Highlights Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                  {[
                    { label: 'Top Speed', value: selectedFileLaps.session.top_speed, unit: 'km/h' },
                    { label: 'Peak RPM', value: selectedFileLaps.session.peak_rpm, unit: '' },
                    { label: 'Fastest Lap', value: selectedFileLaps.session.fastest_lap_time, unit: `s (Lp ${selectedFileLaps.session.fastest_lap_number})` },
                    { label: 'Slowest Lap', value: selectedFileLaps.session.slowest_lap_time, unit: `s (Lp ${selectedFileLaps.session.slowest_lap_number})` },
                    { label: 'Avg Lap Time', value: selectedFileLaps.session.average_lap_time, unit: 's' },
                    { label: 'Std Deviation', value: selectedFileLaps.session.standard_deviation, unit: 's' },
                    { label: 'Pit Stops', value: selectedFileLaps.session.pit_stop_count, unit: `of ${selectedFileLaps.session.total_laps} laps` },
                  ].map((item, i) => (
                    <div key={i} className="p-3 bg-white/5 rounded-lg border border-white/10">
                      <div className="text-xs text-slate-400 uppercase font-semibold">{item.label}</div>
                      <div className="text-white font-mono">
                        {typeof item.value === 'number' ? item.value.toFixed(1) : item.value}
                        {item.unit && <span className="text-slate-400 text-xs ml-1">{item.unit}</span>}
                      </div>
                    </div>
                  ))}
                </div>
                {/* Per-Lap Table */}
                <div className="overflow-x-auto max-h-96 border border-white/10 rounded-lg bg-slate-800/30">
                  <table className="w-full text-left text-sm text-slate-300">
                    <thead className="sticky top-0 bg-slate-900 text-white">
                      <tr>
                        <th className="p-2 border-b border-white/10">Lap</th>
                        <th className="p-2 border-b border-white/10">Duration (s)</th>
                        <th className="p-2 border-b border-white/10">Max Speed</th>
                        <th className="p-2 border-b border-white/10">Avg Speed</th>
                        <th className="p-2 border-b border-white/10">Min Speed</th>
                        <th className="p-2 border-b border-white/10">Max RPM</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedFileLaps.laps.map((lap: any) => {
                        const isFastest = lap.lap_number === selectedFileLaps.session?.fastest_lap_number;
                        const rowClass = lap.is_pit_stop
                          ? 'bg-amber-900/20'
                          : isFastest
                            ? 'bg-emerald-900/20'
                            : '';
                        return (
                          <tr key={lap.lap_number} className={`hover:bg-white/5 transition-colors ${rowClass}`}>
                            <td className="p-2 border-b border-white/5 font-medium text-white">{lap.lap_number}</td>
                            <td className="p-2 border-b border-white/5 font-mono">{lap.duration?.toFixed(1)}</td>
                            <td className="p-2 border-b border-white/5 font-mono">{lap.max_speed?.toFixed(1)}</td>
                            <td className="p-2 border-b border-white/5 font-mono">{lap.avg_speed?.toFixed(1)}</td>
                            <td className="p-2 border-b border-white/5 font-mono">{lap.min_speed?.toFixed(1)}</td>
                            <td className="p-2 border-b border-white/5 font-mono">{lap.max_rpm?.toFixed(0)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : selectedFileLaps && !selectedFileLaps.supported ? (
              <div className="p-6 border-2 border-dashed border-white/10 rounded-2xl text-slate-500 italic text-center">
                Lap data not available for this file.
              </div>
            ) : null}
            </div>
          ) : (
            <div className="h-64 bg-slate-800/50 rounded-xl border border-slate-700 flex items-center justify-center">
              <span className="text-red-400">No summary data found for this file.</span>
            </div>
          )}
        </CardContent>
      </Card>

      <Card variant="glass">
        <CardHeader>
          <CardTitle>Quick Stats</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { label: 'Total Files', value: stats?.total_files },
            { label: 'Active Drivers', value: stats?.active_drivers },
            { label: 'Active Cars', value: stats?.active_cars },
            { label: 'Total Races', value: stats?.total_races },
          ].map((stat, i) => (
            <div key={i} className="flex justify-between items-center p-3 bg-white/5 rounded-lg border border-white/10">
              <span className="text-slate-400">{stat.label}</span>
              <span className="font-mono text-white">{stat.value ?? '...'}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

