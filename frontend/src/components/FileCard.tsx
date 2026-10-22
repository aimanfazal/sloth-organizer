import type { PlanItem } from '../api/types';

const PRIORITY_BADGE: Record<string, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-green-100 text-green-700',
};

interface Props {
  item: PlanItem;
  highlighted: boolean;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export default function FileCard({ item, highlighted, onApprove, onReject }: Props) {
  return (
    <div
      id={`item-${item.id}`}
      className={`rounded-lg border p-4 space-y-3 transition-colors ${
        highlighted ? 'border-gray-500 bg-gray-50 ring-1 ring-gray-400' : 'border-gray-200 bg-white'
      } ${item.applied ? 'opacity-60' : ''}`}
    >
      {/* Filename */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium text-gray-900 break-all">
          {item.source_path.split('/').pop() ?? item.source_path}
        </span>
        {item.priority && (
          <span
            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_BADGE[item.priority] ?? ''}`}
          >
            {item.priority}
          </span>
        )}
      </div>

      {/* Details grid */}
      <div className="space-y-1 text-xs text-gray-500">
        <div className="flex gap-1">
          <span className="w-24 shrink-0 font-medium text-gray-400">Move to</span>
          <span className="text-gray-700">{item.destination}/</span>
        </div>
        {item.new_name && (
          <div className="flex gap-1">
            <span className="w-24 shrink-0 font-medium text-gray-400">Rename</span>
            <span className="text-gray-700">{item.new_name}</span>
          </div>
        )}
        <div className="flex gap-1">
          <span className="w-24 shrink-0 font-medium text-gray-400">Reason</span>
          <span className="text-gray-700">{item.reason}</span>
        </div>
        {item.task && (
          <div className="flex gap-1">
            <span className="w-24 shrink-0 font-medium text-gray-400">Task</span>
            <span className="text-gray-700">{item.task}</span>
          </div>
        )}
        <div className="flex gap-1">
          <span className="w-24 shrink-0 font-medium text-gray-400">Confidence</span>
          <span className="text-gray-700">{(item.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Approve / Reject */}
      {!item.applied && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onApprove(item.id)}
            disabled={item.approved === true}
            className={`flex-1 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              item.approved === true
                ? 'border-green-300 bg-green-50 text-green-700'
                : 'border-gray-200 text-gray-600 hover:border-green-400 hover:bg-green-50 hover:text-green-700'
            }`}
          >
            {item.approved === true ? '✓ Approved' : 'Approve'}
          </button>
          <button
            onClick={() => onReject(item.id)}
            disabled={item.approved === false}
            className={`flex-1 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              item.approved === false
                ? 'border-red-300 bg-red-50 text-red-700'
                : 'border-gray-200 text-gray-600 hover:border-red-400 hover:bg-red-50 hover:text-red-700'
            }`}
          >
            {item.approved === false ? '✗ Rejected' : 'Reject'}
          </button>
        </div>
      )}

      {item.applied && (
        <p className="text-xs text-green-600 font-medium">✓ Applied</p>
      )}
    </div>
  );
}
