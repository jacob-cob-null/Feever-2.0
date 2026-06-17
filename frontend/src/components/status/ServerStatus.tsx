'use client';

import type { HealthResponse } from '@/lib/types';

export function ServerStatus({
  data,
  error,
  isLoading,
}: {
  data: HealthResponse | null;
  error: string | null;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
        <span className="h-2 w-2 rounded-full bg-[var(--text-tertiary)] animate-pulse-subtle" />
        Connecting...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center gap-2 text-xs text-[var(--severity-high)]">
        <span className="h-2 w-2 rounded-full bg-[var(--severity-high)]" />
        Server offline
      </div>
    );
  }

  const isBusy = data.subsystems.inference_lock.status === 'held';

  if (isBusy) {
    return (
      <div className="flex items-center gap-2 text-xs text-[var(--severity-medium)]">
        <span className="h-2 w-2 rounded-full bg-[var(--severity-medium)] animate-pulse-subtle" />
        Processing another document
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs text-[var(--success)]">
      <span className="h-2 w-2 rounded-full bg-[var(--success)]" />
      System ready &middot; v{data.version}
    </div>
  );
}
