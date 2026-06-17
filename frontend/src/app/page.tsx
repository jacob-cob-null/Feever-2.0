'use client';

import { useCallback, useReducer, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { WorkflowState, WorkflowAction, ApiError } from '@/lib/types';
import { useHealthCheck } from '@/hooks/useHealthCheck';
import { useAnalyze } from '@/hooks/useAnalyze';
import { ServerStatus } from '@/components/status/ServerStatus';
import { UploadPanel } from '@/components/upload/UploadPanel';
import { ProcessingView } from '@/components/processing/ProcessingView';
import { ResultsView } from '@/components/results/ResultsView';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

function workflowReducer(state: WorkflowState, action: WorkflowAction): WorkflowState {
  switch (action.type) {
    case 'START_UPLOAD':
      return { phase: 'processing', file: action.file, startedAt: Date.now() };
    case 'UPLOAD_SUCCESS':
      if (state.phase !== 'processing') return state;
      return { phase: 'results', file: state.file, data: action.data };
    case 'UPLOAD_ERROR':
      return {
        phase: 'error',
        file: state.phase === 'processing' ? state.file : null,
        error: action.error,
      };
    case 'RESET':
      return { phase: 'idle' };
    default:
      return state;
  }
}

const ERROR_MESSAGES: Record<string, { title: string; description: string; canRetry: boolean }> = {
  busy: {
    title: 'Server is busy',
    description: 'Another document is currently being analyzed. Please wait for it to finish and try again.',
    canRetry: true,
  },
  not_ready: {
    title: 'Server is starting up',
    description: 'The analysis model is still loading. This typically takes 1\u20132 minutes after server start.',
    canRetry: true,
  },
  invalid_image: {
    title: 'Invalid image',
    description: 'The uploaded file could not be processed.',
    canRetry: true,
  },
  extraction_failed: {
    title: 'Extraction failed',
    description: 'The model could not extract structured data from this image. Try a clearer, higher-resolution photo.',
    canRetry: true,
  },
  inference_timeout: {
    title: 'Processing timed out',
    description: 'The analysis took too long and was canceled. The image may be too complex.',
    canRetry: true,
  },
  network_error: {
    title: 'Connection lost',
    description: 'Could not reach the analysis server. Verify the backend is running.',
    canRetry: true,
  },
  internal_error: {
    title: 'Server error',
    description: 'An unexpected error occurred on the server.',
    canRetry: true,
  },
};

function ErrorView({ error, onReset }: { error: ApiError; onReset: () => void }) {
  const config = ERROR_MESSAGES[error.error_type] || {
    title: 'Something went wrong',
    description: error.detail,
    canRetry: true,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-xl mx-auto"
    >
      <Card borderColor="var(--severity-high)">
        <div className="space-y-4">
          <div>
            <h2
              className="text-xl text-[var(--severity-high)]"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              {config.title}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
              {error.detail || config.description}
            </p>
          </div>

          {error.request_id && (
            <p className="text-xs text-[var(--text-tertiary)]" style={{ fontFamily: 'var(--font-mono)' }}>
              Request ID: {error.request_id}
            </p>
          )}

          {config.canRetry && (
            <Button onClick={onReset} variant="secondary">
              Try Again
            </Button>
          )}
        </div>
      </Card>
    </motion.div>
  );
}

export default function Home() {
  const [state, dispatch] = useReducer(workflowReducer, { phase: 'idle' });
  const isProcessing = state.phase === 'processing';
  const health = useHealthCheck(10_000, isProcessing);
  const { submit, cancel } = useAnalyze(dispatch);
  const lastConsentRef = useRef(false);

  const handleSubmit = useCallback(
    (file: File, consent: boolean) => {
      lastConsentRef.current = consent;
      submit(file, consent);
    },
    [submit],
  );

  const handleRetry = useCallback(() => {
    if (state.phase === 'results') {
      submit(state.file, lastConsentRef.current);
    }
  }, [state, submit]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]">
        <div className="flex items-center gap-3">
          <h1
            className="text-xl tracking-tight text-[var(--text-primary)]"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Fee-Ver
          </h1>
          <span className="text-xs text-[var(--text-tertiary)] font-medium tracking-wide uppercase">
            Medical Billing Analysis
          </span>
        </div>
        <ServerStatus data={health.data} error={health.error} isLoading={health.isLoading} />
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <AnimatePresence mode="wait">
          {state.phase === 'idle' && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="w-full"
            >
              <div className="text-center mb-10">
                <h2
                  className="text-4xl text-[var(--text-primary)] mb-3"
                  style={{ fontFamily: 'var(--font-serif)' }}
                >
                  Verify hospital invoices
                </h2>
                <p className="text-base text-[var(--text-secondary)] max-w-md mx-auto leading-relaxed">
                  Upload a billing document to automatically cross-reference charges against PhilHealth case rates and hospital service schedules.
                </p>
              </div>
              <UploadPanel
                onSubmit={handleSubmit}
                isReady={health.isReady}
                isBusy={health.isBusy}
              />
            </motion.div>
          )}

          {state.phase === 'processing' && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="w-full"
            >
              <ProcessingView
                file={state.file}
                startedAt={state.startedAt}
                onCancel={() => {
                  cancel();
                  dispatch({ type: 'RESET' });
                }}
              />
            </motion.div>
          )}

          {state.phase === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="w-full"
            >
              <ResultsView
                data={state.data}
                onReset={() => dispatch({ type: 'RESET' })}
                onRetry={handleRetry}
              />
            </motion.div>
          )}

          {state.phase === 'error' && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="w-full"
            >
              <ErrorView
                error={state.error}
                onReset={() => dispatch({ type: 'RESET' })}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
