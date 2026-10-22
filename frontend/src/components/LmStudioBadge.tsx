import type { LmStudioStatus } from '../api/types';

interface Props {
  status: LmStudioStatus | null;
  loading: boolean;
}

export default function LmStudioBadge({ status, loading }: Props) {
  if (loading) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs text-gray-500">
        <span className="h-2 w-2 animate-pulse rounded-full bg-gray-400" />
        Checking LM Studio…
      </span>
    );
  }

  if (status?.connected) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-green-200 bg-green-50 px-3 py-1 text-xs text-green-700">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        {status.model ? `LM Studio · ${status.model}` : 'LM Studio connected'}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs text-amber-700">
      <span className="h-2 w-2 rounded-full bg-amber-400" />
      LM Studio not detected
    </span>
  );
}
