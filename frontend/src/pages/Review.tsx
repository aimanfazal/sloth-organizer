import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getPlan, updateItemApproval } from '../api/client';
import type { PlanDetail, PlanItem } from '../api/types';
import FileCard from '../components/FileCard';

export default function Review() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const planId = searchParams.get('plan_id') ?? '';
  const scanId = searchParams.get('scan_id') ?? '';
  const highlight = searchParams.get('highlight') ?? '';

  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [items, setItems] = useState<PlanItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const highlightRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!planId) { setError('No plan ID in URL'); return; }
    getPlan(planId)
      .then((p) => {
        setPlan(p);
        setItems(p.items);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load plan'));
  }, [planId]);

  // Scroll to highlighted item once items load
  useEffect(() => {
    if (!highlight || items.length === 0) return;
    const el = document.getElementById(`item-${highlight}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlight, items]);

  async function handleApprove(itemId: string) {
    // Optimistic update
    setItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, approved: true } : i)));
    try {
      await updateItemApproval(planId, itemId, true);
    } catch {
      // Roll back on failure
      setItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, approved: null } : i)));
    }
  }

  async function handleReject(itemId: string) {
    setItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, approved: false } : i)));
    try {
      await updateItemApproval(planId, itemId, false);
    } catch {
      setItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, approved: null } : i)));
    }
  }

  const approvedCount = items.filter((i) => i.approved === true).length;
  const canApply = approvedCount > 0;

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

  return (
    <div className="min-h-screen bg-white px-4 py-10">
      <div className="mx-auto max-w-xl space-y-6" ref={highlightRef}>
        {/* Header */}
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-gray-900">Review Changes</h2>
          <p className="text-sm text-gray-400">
            {items.length} proposed {items.length === 1 ? 'change' : 'changes'} · {approvedCount} approved
          </p>
        </div>

        {/* Cards */}
        <div className="space-y-3">
          {items.map((item) => (
            <FileCard
              key={item.id}
              item={item}
              highlighted={item.id === highlight}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ))}
        </div>

        {/* Footer nav */}
        <div className="sticky bottom-0 bg-white border-t border-gray-100 py-4 flex gap-3">
          <button
            onClick={() => navigate(`/tasks?scan_id=${scanId}&plan_id=${planId}`)}
            className="rounded-lg border border-gray-200 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            ← Tasks
          </button>
          <button
            onClick={() => navigate(`/apply?scan_id=${scanId}&plan_id=${planId}`)}
            disabled={!canApply}
            className="flex-1 rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-700 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            Continue to Apply →
          </button>
        </div>
      </div>
    </div>
  );
}
