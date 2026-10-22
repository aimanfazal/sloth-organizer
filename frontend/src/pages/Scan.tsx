import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { openScanSocket } from '../api/client';
import type { WsCompleteMessage, WsMessage } from '../api/types';

type ScanState = 'scanning' | 'complete' | 'error';

interface Summary {
  file_count: number;
  folder_count: number;
  duplicate_groups: number;
  total_size_bytes: number;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_073_741_824) return (bytes / 1_073_741_824).toFixed(1) + ' GB';
  if (bytes >= 1_048_576) return (bytes / 1_048_576).toFixed(1) + ' MB';
  if (bytes >= 1_024) return (bytes / 1_024).toFixed(1) + ' KB';
  return bytes + ' B';
}

export default function Scan() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const scanId = searchParams.get('scan_id') ?? '';

  const [state, setState] = useState<ScanState>('scanning');
  const [percent, setPercent] = useState(0);
  const [stage, setStage] = useState('Connecting…');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const retriedRef = useRef(false);

  useEffect(() => {
    if (!scanId) {
      setError('No scan ID in URL');
      setState('error');
      return;
    }

    function connect() {
      const ws = openScanSocket(scanId);
      wsRef.current = ws;

      ws.onmessage = (event: MessageEvent) => {
        let msg: WsMessage;
        try {
          msg = JSON.parse(event.data as string) as WsMessage;
        } catch {
          return;
        }

        if (msg.type === 'progress') {
          setPercent(msg.percent);
          setStage(msg.stage);
        } else if (msg.type === 'complete') {
          setSummary((msg as WsCompleteMessage).summary);
          setState('complete');
          ws.close();
        } else if (msg.type === 'error') {
          setError(msg.detail);
          setState('error');
          ws.close();
        }
      };

      ws.onerror = () => {
        if (!retriedRef.current) {
          retriedRef.current = true;
          ws.close();
          setTimeout(connect, 1000);
        } else {
          setError('WebSocket connection failed');
          setState('error');
        }
      };

      ws.onclose = () => {
        // If closed before complete without an explicit error, treat as dropped
        if (state === 'scanning' && !retriedRef.current) {
          retriedRef.current = true;
          setTimeout(connect, 1000);
        }
      };
    }

    connect();
    return () => {
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanId]);

  function handleContinue() {
    navigate(`/organize?scan_id=${scanId}`);
  }

  // --- Scanning view ---
  if (state === 'scanning') {
    const clamped = Math.min(100, Math.max(0, percent));
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-500">Scanning…</p>
            <p className="mt-1 text-xl font-semibold text-gray-900">{clamped}%</p>
          </div>

          {/* Progress bar */}
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full bg-gray-900 transition-all duration-300"
              style={{ width: `${clamped}%` }}
            />
          </div>

          {/* Stage labels */}
          <div className="space-y-1">
            {['Finding files…', 'Reading metadata…', 'Detecting duplicates…', 'Preparing AI context…'].map(
              (label) => (
                <p
                  key={label}
                  className={`text-sm ${label === stage ? 'font-medium text-gray-900' : 'text-gray-300'}`}
                >
                  {label}
                </p>
              ),
            )}
          </div>
        </div>
      </div>
    );
  }

  // --- Error view ---
  if (state === 'error') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
        <div className="w-full max-w-md rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-red-700">Scan failed</p>
          <p className="mt-1 text-xs text-red-500">{error ?? 'Unknown error'}</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 rounded-lg bg-gray-900 px-4 py-2 text-sm text-white hover:bg-gray-700"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    );
  }

  // --- Complete view ---
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="text-4xl">🦥</div>
          <h2 className="mt-2 text-xl font-semibold text-gray-900">Scan complete</h2>
        </div>

        {summary && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 divide-y divide-gray-200">
            {[
              ['Files', summary.file_count.toLocaleString()],
              ['Folders', summary.folder_count.toLocaleString()],
              ['Duplicate groups', summary.duplicate_groups.toLocaleString()],
              ['Total size', formatBytes(summary.total_size_bytes)],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between px-4 py-3">
                <span className="text-sm text-gray-500">{label}</span>
                <span className="text-sm font-medium text-gray-900">{value}</span>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={handleContinue}
          className="w-full rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-700"
        >
          Continue →
        </button>
      </div>
    </div>
  );
}
