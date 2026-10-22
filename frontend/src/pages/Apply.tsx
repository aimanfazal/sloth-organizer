import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { applyPlan, getPlan } from '../api/client';
import type { ApplyResponse, PlanDetail } from '../api/types';

type ApplyState = 'idle' | 'applying' | 'done' | 'error';

export default function Apply() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const planId = searchParams.get('plan_id') ?? '';
  const scanId = searchParams.get('scan_id') ?? '';

  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [applyState, setApplyState] = useState<ApplyState>('idle');
  const [result, setResult] = useState<ApplyResponse | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);

  useEffect(() => {
    if (!planId) { setLoadError('No plan ID in URL'); return; }
    getPlan(planId)
      .then(setPlan)
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : 'Failed to load plan'));
  }, [planId]);

  async function handleApply() {
    if (!plan) return;
    const approvedIds = plan.items.filter((i) => i.approved === true).map((i) => i.id);
    setApplyState('applying');
    setApplyError(null);
    try {
      const res = await applyPlan(planId, { approved_items: approvedIds, dry_run: false });
      setResult(res);
      setApplyState('done');
    } catch (err: unknown) {
      setApplyError(err instanceof Error ? err.message : 'Apply failed');
      setApplyState('error');
    }
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white px-4">
        <p className="text-sm text-red-600">{loadError}</p>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-gray-700" />
      </div>
    );
  }

  const approvedItems = plan.items.filter((i) => i.approved === true);
  const skippedItems = plan.items.filter((i) => i.approved !== true);

  // --- Pre-apply summary ---
  if (applyState === 'idle' || applyState === 'error') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center space-y-1">
            <div className="text-4xl">🦥</div>
            <h2 className="text-xl font-semibold text-gray-900">Ready to organize?</h2>
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 divide-y divide-gray-200">
            {[
              [`${approvedItems.length} files will move`, approvedItems.length > 0],
              ['0 files will be deleted', true],
              [`${skippedItems.length} files will be skipped (not approved)`, skippedItems.length > 0],
            ].map(([label, show]) =>
              show ? (
                <div key={label as string} className="px-4 py-3 text-sm text-gray-700">
                  {label as string}
                </div>
              ) : null,
            )}
          </div>

          {applyState === 'error' && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
              {applyError}
            </p>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => navigate(`/review?scan_id=${scanId}&plan_id=${planId}`)}
              className="rounded-lg border border-gray-200 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
            >
              ← Review Changes
            </button>
            <button
              onClick={handleApply}
              disabled={approvedItems.length === 0}
              className="flex-1 rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              🦥 Apply Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- Applying ---
  if (applyState === 'applying') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
        <div className="text-center space-y-4">
          <div className="text-5xl animate-bounce">🦥</div>
          <p className="text-lg font-semibold text-gray-900">Moving files…</p>
        </div>
      </div>
    );
  }

  // --- Done ---
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-1">
          <div className="text-4xl">✅</div>
          <h2 className="text-xl font-semibold text-gray-900">Done!</h2>
        </div>

        {result && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 divide-y divide-gray-200">
            {[
              ['Moved', result.moved],
              ['Renamed', result.renamed],
              ['Skipped', result.skipped],
            ].map(([label, val]) => (
              <div key={label as string} className="flex justify-between px-4 py-3">
                <span className="text-sm text-gray-500">{label as string}</span>
                <span className="text-sm font-medium text-gray-900">{val as number}</span>
              </div>
            ))}
          </div>
        )}

        {result && result.errors.length > 0 && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 space-y-1">
            <p className="text-xs font-medium text-red-700">Errors ({result.errors.length})</p>
            {result.errors.map((e) => (
              <p key={e.item_id} className="text-xs text-red-600">{e.detail}</p>
            ))}
          </div>
        )}

        <p className="text-center text-xs text-gray-400">
          Files were moved, not deleted. You can move them back manually.
        </p>

        <button
          onClick={() => navigate('/')}
          className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
        >
          ← Start over
        </button>
      </div>
    </div>
  );
}
