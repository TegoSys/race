import React, { useState } from 'react';
import apiClient from '../lib/api';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

export const Upload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>('');

  const handleUpload = async () => {
    if (!file) return;
    setStatus('Uploading...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiClient.post('/upload', formData);
      setStatus(`Uploaded! File ID: ${response.data.file_id}`);
    } catch (error) {
      setStatus('Upload failed.');
      console.error(error);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <Card variant="glass">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl">Upload Race Data</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          <div className="border-2 border-dashed border-slate-700 rounded-xl p-12 mb-6 hover:border-blue-500 transition-colors cursor-pointer relative bg-white/5">
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="absolute inset-0 opacity-0 cursor-pointer"
              accept=".csv"
            />
            <p className="text-slate-400">
              {file ? `Selected: ${file.name}` : 'Drag and drop or click to select a CSV file'}
            </p>
          </div>
          <div className="flex flex-col items-center gap-4">
            <Button
              onClick={handleUpload}
              variant="primary"
              size="lg"
              disabled={!file}
            >
              Upload to Server
            </Button>
            {status && <p className="text-slate-400 text-sm">{status}</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
