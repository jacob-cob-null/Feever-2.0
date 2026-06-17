'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { checkHealth } from '@/lib/api';
import type { HealthResponse } from '@/lib/types';

interface HealthState {
  data: HealthResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function useHealthCheck(intervalMs: number = 10_000, paused: boolean = false) {
  const [state, setState] = useState<HealthState>({
    data: null,
    isLoading: true,
    error: null,
  });
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  const poll = useCallback(async () => {
    try {
      const data = await checkHealth();
      setState({ data, isLoading: false, error: null });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Connection failed',
      }));
    }
  }, []);

  // Initial poll on mount
  useEffect(() => {
    poll();
  }, [poll]);

  // Interval polling — stops when paused
  useEffect(() => {
    if (paused) return;

    const id = setInterval(poll, intervalMs);
    return () => clearInterval(id);
  }, [poll, intervalMs, paused]);

  const isReady =
    state.data?.status === 'ok' &&
    state.data.subsystems.model.status === 'loaded';
  const isBusy = state.data?.subsystems.inference_lock.status === 'held';

  return { ...state, isReady, isBusy, poll };
}
