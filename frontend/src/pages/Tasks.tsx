import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getPlan } from '../api/client';
import type { PlanDetail, PlanItem } from '../api/types';

const PRIORITY_CONFIG = {
  high: { icon: '🔥', label: 'HIGH', order: 0 },
  medium: { icon: '🟡', label: 'MEDIUM', order: 1 },
  low: { icon: '🟢', label: 'LOW', order: 2 },
} as const;

type Priority = keyof typeof PRIORITY_CONFIG;

export default function Tasks() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const planId = searchParams.get('plan_id') ?? '';
  const scanId = searchParams.get('scan_id') ?? '';

  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!planId) { setError('No plan ID in URL'); return; }
    getPlan(planId)
      .then(setPlan)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load plan'));
  }, [planId]);

  function handleContinue() {
    navigate(`/review?scan_id=${scanId}&plan_id=${planId}`);
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white px-4">
        <p className="text-sm text-red-600">{error}</p>
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

  // Filter to items with tasks, group by priority
  const taskItems = plan.items.filter((i): i is PlanItem => i.task !== null);
  const grouped = Object.fromEntries(
    (['high', 'medium', 'low'] as Priority[]).map((p) => [p, taskItems.filter((i) => i.priority === p)]),
  );
  // Items with null priority fall into a misc bucket shown last
  const noPriority = taskItems.filter((i) => i.priority === null);

  return (
    <div className="flex min-h-screen flex-col items-center bg-white px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-1">
          <div className="text-4xl">🦥</div>
          <h2 className="text-xl font-semibold text-gray-900">Your actual workload</h2>
          <p className="text-sm text-gray-400">
            {taskItems.length === 0
              ? 'No action items — everything can be organized automatically.'
              : `${taskItems.length} ${taskItems.length === 1 ? 'thing needs' : 'things need'} you.`}
          </p>
        </div>

        {(['high', 'medium', 'low'] as Priority[]).map((priority) => {
          const items = grouped[priority];
          if (items.length === 0) return null;
          const cfg = PRIORITY_CONFIG[priority];
          return (
            <section key={priority} className="space-y-2">
              <p className="text-xs font-semibold tracking-widest text-gray-400 uppercase">
                {cfg.icon} {cfg.label}
              </p>
              <ul className="space-y-1.5">
                {items.map((item) => (
                  <li key={item.id}>
                    <button
                      onClick={() => navigate(`/review?scan_id=${scanId}&plan_id=${planId}&highlight=${item.id}`)}
                      className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-left text-sm text-gray-800 hover:border-gray-400 hover:bg-white transition-colors"
                    >
                      {item.task}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}

        {noPriority.length > 0 && (
          <section className="space-y-2">
            <p className="text-xs font-semibold tracking-widest text-gray-400 uppercase">OTHER</p>
            <ul className="space-y-1.5">
              {noPriority.map((item) => (
                <li key={item.id}>
                  <button
                    onClick={() => navigate(`/review?scan_id=${scanId}&plan_id=${planId}&highlight=${item.id}`)}
                    className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-left text-sm text-gray-800 hover:border-gray-400 hover:bg-white transition-colors"
                  >
                    {item.task}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {taskItems.length === 0 && (
          <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-6 text-center text-sm text-gray-400">
            No tasks generated.
          </div>
        )}

        <button
          onClick={handleContinue}
          className="w-full rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-700"
        >
          Review All Changes →
        </button>
      </div>
    </div>
  );
}
