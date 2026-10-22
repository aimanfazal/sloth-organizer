import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLmStudioStatus, startScan } from '../api/client';
import type { LmStudioStatus } from '../api/types';
import LmStudioBadge from '../components/LmStudioBadge';

export default function Home() {
  const navigate = useNavigate();
  const [folder, setFolder] = useState('');
  const [lmStatus, setLmStatus] = useState<LmStudioStatus | null>(null);
  const [lmLoading, setLmLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Check LM Studio connectivity on mount
  useEffect(() => {
    getLmStudioStatus()
      .then(setLmStatus)
      .catch(() => setLmStatus({ connected: false, model: null }))
      .finally(() => setLmLoading(false));
  }, []);

  const canScan = !lmLoading && (lmStatus?.connected ?? false) && folder.trim().length > 0 && !scanning;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canScan) return;
    setError(null);
    setScanning(true);
    try {
      const { scan_id } = await startScan(folder.trim());
      navigate(`/scan?scan_id=${scan_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scan');
      setScanning(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
      <div className="w-full max-w-md space-y-8">

        {/* Header */}
        <div className="text-center">
          <div className="text-5xl">🦥</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-gray-900">
            Sloth Organizer
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Give your messy folder to the sloth.
          </p>
        </div>

        {/* LM Studio status */}
        <div className="flex justify-center">
          <LmStudioBadge status={lmStatus} loading={lmLoading} />
        </div>

        {/* Scan form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <label htmlFor="folder-input" className="block text-sm font-medium text-gray-700">
            Folder path
          </label>
          <input
            id="folder-input"
            ref={inputRef}
            type="text"
            value={folder}
            onChange={e => setFolder(e.target.value)}
            placeholder="/Users/you/Downloads"
            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            disabled={scanning}
          />

          {/* Disabled-state tooltip wrapper */}
          <div
            title={
              lmLoading
                ? 'Checking LM Studio…'
                : !lmStatus?.connected
                  ? 'LM Studio must be running before you can scan'
                  : folder.trim().length === 0
                    ? 'Enter a folder path first'
                    : undefined
            }
          >
            <button
              type="submit"
              disabled={!canScan}
              className="w-full rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              {scanning ? 'Starting scan…' : 'Select Folder'}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {/* Footer note */}
        <p className="text-center text-xs text-gray-400">
          Your files stay on your machine.{' '}
          <span className="whitespace-nowrap">AI runs locally through LM Studio.</span>
        </p>
      </div>
    </div>
  );
}
