import React, { useState, useEffect } from 'react';
import {
  ScatterChart, Scatter, Line, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend
} from 'recharts';
import apiClient from '../lib/api';
import { projectGPS } from '../utils/gpsUtils';
import { Card } from './ui/Card';

interface GPSPoint {
  lat: number;
  lon: number;
  x?: number;
  y?: number;
}

export const TrackPlot = ({ fileId }: { fileId: string }) => {
  const [plotState, setPlotState] = useState<{
    data: { x: number; y: number; lat: number; lon: number }[],
    domains: { x: [number, number], y: [number, number] }
  }>({
    data: [],
    domains: { x: [-1, 1], y: [-1, 1] }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [venueName, setVenueName] = useState<string>('Race Track');
  const [driverName, setDriverName] = useState<string>('');

  useEffect(() => {
    const fetchGPSData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch summary to extract venue name from metadata
        const summaryRes = await apiClient.get(`/files/${fileId}/summary`);
        const meta = summaryRes.data?.metadata;
        const parsedMeta = typeof meta === 'string' ? JSON.parse(meta) : meta;
        const venue = parsedMeta?.Venue || parsedMeta?.venue || '';
        const parsedVenue = venue.split(',')[0].replace(/"/g, '').trim() || 'Race Track';
        setVenueName(parsedVenue);

        const driver = parsedMeta?.Driver || parsedMeta?.driver || '';
        const parsedDriver = driver.split(',')[0].replace(/"/g, '').trim() || '';
        setDriverName(parsedDriver);

        // We explicitly request the GPS columns
        const res = await apiClient.get('/files/data', {
          params: {
            file_id: fileId,
            columns: 'GPS Latitude,GPS Longitude',
            downsample_factor: 100 // Use default downsampling to prevent render overhead
          }
        });

        const rawData = res.data as any[];

        // 1. Collect non-zero GPS values and compute medians for data-driven filtering
        const lats = rawData.map(r => r['GPS Latitude'])
          .filter(v => v !== 0 && v != null && !isNaN(v))
          .sort((a, b) => a - b);
        const lons = rawData.map(r => r['GPS Longitude'])
          .filter(v => v !== 0 && v != null && !isNaN(v))
          .sort((a, b) => a - b);

        if (lats.length === 0 || lons.length === 0) {
          throw new Error('No valid GPS coordinates found for this file.');
        }

        const medianLat = lats[Math.floor(lats.length / 2)];
        const medianLon = lons[Math.floor(lons.length / 2)];

        // 2. Filter out zeros, nulls, and points outside a tight band around the medians
        const latTolerance = 0.05; // ~5.5km latitude tolerance
        const lonTolerance = 0.05;
        const validPoints = rawData.filter(row => {
          const lat = row['GPS Latitude'];
          const lon = row['GPS Longitude'];

          if (lat === 0 || lon === 0 || lat === null || lon === null) return false;
          if (Math.abs(lat - medianLat) > latTolerance) return false;
          if (Math.abs(lon - medianLon) > lonTolerance) return false;

          return true;
        }).map(row => ({
          lat: row['GPS Latitude'],
          lon: row['GPS Longitude']
        }));

        if (validPoints.length === 0) {
          throw new Error('No valid GPS coordinates found for this file.');
        }

        // 2. Outlier Removal (Distance-based spikes)
        // Increase threshold to 250m to avoid cutting laps at high speed
        const cleanedPoints: GPSPoint[] = [];
        if (validPoints.length > 0) {
          cleanedPoints.push(validPoints[0]);
          for (let i = 1; i < validPoints.length; i++) {
            const prev = cleanedPoints[cleanedPoints.length - 1];
            const curr = validPoints[i];

            const pPrev = projectGPS(prev.lat, prev.lon, prev.lat, prev.lon);
            const pCurr = projectGPS(curr.lat, curr.lon, prev.lat, prev.lon);
            const dist = Math.sqrt(Math.pow(pCurr.x, 2) + Math.pow(pCurr.y, 2));

            if (dist < 250) { // Increased spike threshold
              cleanedPoints.push(curr);
            }
          }
        }

        // 3. Projection relative to the first valid point
        const origin = cleanedPoints[0];
        const projectedData = cleanedPoints.map(pt => {
          const { x, y } = projectGPS(pt.lat, pt.lon, origin.lat, origin.lon);
          return { x, y, lat: pt.lat, lon: pt.lon };
        });









        

        // 4. Calculate Aspect-Ratio Preserving Domains
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        for (const p of projectedData) {
          if (p.x < minX) minX = p.x;
          if (p.x > maxX) maxX = p.x;
          if (p.y < minY) minY = p.y;
          if (p.y > maxY) maxY = p.y;
        }

        const xRange = maxX - minX;
        const yRange = maxY - minY;

        const center_x = (minX + maxX) / 2;
        const center_y = (minY + maxY) / 2;
        const maxDim = Math.max(xRange, yRange);

        setPlotState({
          data: projectedData,
          domains: {
            x: [center_x - maxDim / 2, center_x + maxDim / 2],
            y: [center_y - maxDim / 2, center_y + maxDim / 2]
          }
        });
      } catch (e: any) {
        setError(e.message || 'Failed to fetch GPS data');
      } finally {
        setLoading(false);
      }
    };

    fetchGPSData();
  }, [fileId]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-white font-medium">
        Loading Track Plot...
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400 italic border-2 border-dashed border-white/10 rounded-2xl min-h-[600px]">
        {error}
      </div>
    );
  }

  return (
    <Card variant="glass" className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-white">{venueName}</h3>
        {driverName && <span className="text-sm text-slate-300">{driverName}</span>}
        <span className="text-xs text-slate-400 font-mono">Units: Meters</span>
      </div>
      <div className="flex-1 w-full max-w-[800px] mx-auto h-[600px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis
              type="number"
              dataKey="x"
              name="East-West"
              stroke="#94a3b8"
              fontSize={12}
              domain={plotState.domains.x}
              tickFormatter={(val) => `${val.toFixed(0)}m`}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="North-South"
              stroke="#94a3b8"
              fontSize={12}
              domain={plotState.domains.y}
              tickFormatter={(val) => `${val.toFixed(0)}m`}
            />
            <ZAxis range={[1, 1]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const pt = payload[0].payload as { x: number; y: number; lat: number; lon: number };
                return (
                  <div style={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '8px 12px', borderRadius: '6px' }}>
                    <div className="text-sm font-medium mb-1">GPS: {pt.lat.toFixed(6)}, {pt.lon.toFixed(6)}</div>
                    <div className="text-xs text-slate-300">E-W: {pt.x.toFixed(2)}m</div>
                    <div className="text-xs text-slate-300">N-S: {pt.y.toFixed(2)}m</div>
                  </div>
                );
              }}
            />
            
            <Scatter
              name="Vehicle Path"
              data={plotState.data}
              fill="#3b82f6"
              fillOpacity={0}
              line stroke="#3b82f6" strokeWidth={1}
              shape={(props) => {
    // This renders an invisible structural circle that still catches mouse hovers
                return <circle cx={props.cx} cy={props.cy} r={6} fill="transparent" stroke="transparent" />;
              }}
            />
          </ScatterChart>
          
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
