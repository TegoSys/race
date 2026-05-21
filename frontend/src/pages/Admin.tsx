import React, { useState, useEffect } from 'react';
import apiClient from '../lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

interface FileRecord {
  id: number;
  filename: string;
  file_path: string;
  driver_id: number | null;
  car_id: number | null;
  race_id: number | null;
  metadata_json: any;
}

export const Admin: React.FC = () => {
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string, type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/files');
      setFiles(res.data);
    } catch (e) {
      console.error('Error fetching files', e);
      setMessage({ text: 'Failed to fetch files.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const toggleSelection = (id: number) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleDelete = async () => {
    if (selectedIds.length === 0) return;

    if (!window.confirm(`Are you sure you want to delete ${selectedIds.length} file(s)? This action cannot be undone.`)) {
      return;
    }

    setLoading(true);
    setMessage(null);
    try {
      await Promise.all(selectedIds.map(id => apiClient.delete(`/files/${id}`)));
      setMessage({ text: `Successfully deleted ${selectedIds.length} file(s).`, type: 'success' });
      setSelectedIds([]);
      await fetchFiles();
    } catch (e) {
      console.error('Error deleting files', e);
      setMessage({ text: 'An error occurred while deleting files.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold text-white">System Administration</h2>
          <p className="text-slate-400">Manage raw race data files and cleanup system storage.</p>
        </div>
        <button
          onClick={handleDelete}
          disabled={selectedIds.length === 0 || loading}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            selectedIds.length === 0 || loading
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/50'
          }`}
        >
          Delete Selected ({selectedIds.length})
        </button>
      </div>

      {message && (
        <div className={`p-4 rounded-lg border ${
          message.type === 'success'
            ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400'
            : 'bg-red-500/10 border-red-500/50 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      <Card variant="glass">
        <CardHeader>
          <CardTitle>Stored Data Files</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-slate-400 border-b border-white/10">
                <tr>
                  <th className="py-3 px-4 w-12">
                    <input
                      type="checkbox"
                      checked={selectedIds.length === files.length && files.length > 0}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedIds(files.map(f => f.id));
                        else setSelectedIds([]);
                      }}
                      className="accent-blue-500"
                    />
                  </th>
                  <th className="py-3 px-4 font-medium">File ID</th>
                  <th className="py-3 px-4 font-medium">Filename</th>
                  <th className="py-3 px-4 font-medium">Driver ID</th>
                  <th className="py-3 px-4 font-medium">Car ID</th>
                  <th className="py-3 px-4 font-medium">Race ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {loading && files.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500 italic">Loading files...</td>
                  </tr>
                ) : files.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500 italic">No files found in the system.</td>
                  </tr>
                ) : (
                  files.map(file => (
                    <tr
                      key={file.id}
                      className={`hover:bg-white/5 transition-colors ${selectedIds.includes(file.id) ? 'bg-white/10' : ''}`}
                    >
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(file.id)}
                          onChange={() => toggleSelection(file.id)}
                          className="accent-blue-500"
                        />
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">{file.id}</td>
                      <td className="py-3 px-4 text-white font-medium">{file.filename}</td>
                      <td className="py-3 px-4 text-slate-300">{file.driver_id ?? 'N/A'}</td>
                      <td className="py-3 px-4 text-slate-300">{file.car_id ?? 'N/A'}</td>
                      <td className="py-3 px-4 text-slate-300">{file.race_id ?? 'N/A'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
