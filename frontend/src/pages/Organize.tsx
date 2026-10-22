import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { createPlan } from '../api/client';
import type { PlanResponse } from '../api/types';

type OrganizeState = 'loading' | 'done' | 'error';

export default function Organize() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const scanId = searchParams.get('scan_id') ?? '';

  const [state, setState] = useState<OrganizeState>('loading');
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(() => {
    if (!scanId) {
      setError('No scan ID in URL');
      setState('error');
      return;
    }
    setState('loading');
    setError(null);
    createPlan(scanId)
      .then((p) => {
        setPlan(p);
        setState('done');
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Plan generation failed');
        setState('error');
      });
  }, [scanId]);

  useEffect(() => {
    generate();
  }, [generate]);

  function handleContinue() {
    if (plan) {
      navigate(`/tasks?scan_id=${scanId}&plan_id=${plan.plan_id}`);
    }
  }

  // --- Loading ---
  if (state === 'loading') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
        <div className="text-center space-y-4">
          <div className="text-5xl animate-bounce">🦥</div>
          <p className="text-lg font-semibold text-gray-900">Sloth is thinking…</p>
          <p className="text-sm text-gray-400">This can take a minute while the model runs locally.</p>
        </div>
      </div>
    );
  }

  // --- Error ---
  if (state === 'error') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
        <div className="w-full max-w-md rounded-lg border border-red-200 bg-red-50 p-6 text-center space-y-3">
          <p className="text-sm font-medium text-red-700">Plan generation failed</p>
          <p className="text-xs text-red-500">{error}</p>
          <button
            onClick={generate}
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm text-white hover:bg-gray-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // --- Done ---
  // Build folder breakdown: group items by destination, count
  const folderCounts = (plan?.items ?? []).reduce<Record<string, number>>((acc, item) => {
    acc[item.destination] = (acc[item.destination] ?? 0) + 1;
    return acc;
  }, {});
  const folders = Object.entries(folderCounts).sort((a, b) => b[1] - a[1]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-1">
          <div className="text-4xl">🧠</div>
          <h2 className="text-xl font-semibold text-gray-900">Sloth's Plan</h2>
          {plan?.summary && (
            <p className="text-sm text-gray-500">{plan.summary}</p>
          )}
        </div>

        {/* Folder breakdown */}
        <div className="rounded-lg border border-gray-200 bg-gray-50 divide-y divide-gray-200">
          {folders.map(([folder, count]) => (
            <div key={folder} className="flex items-center justify-between px-4 py-3">
              <span className="text-sm text-gray-700">{folder}</span>
              <span className="text-sm font-medium text-gray-900">
                {count} {count === 1 ? 'file' : 'files'}
              </span>
            </div>
          ))}
        </div>

        <button
          onClick={handleContinue}
          className="w-full rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-700"
        >
          View Tasks →
        </button>
      </div>
    </div>
  );
}
