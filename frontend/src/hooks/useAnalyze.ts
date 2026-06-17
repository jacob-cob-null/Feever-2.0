'use client';

import { useCallback, useRef } from 'react';
import { analyzeDocument, ApiRequestError } from '@/lib/api';
import type { AnalyzeResponse, ApiError, WorkflowAction } from '@/lib/types';

const TIMEOUT_MS = 300_000; // 5 minutes — backend inference can take 60-120s
const MAX_RETRIES = 1; // auto-retry once on empty extraction

function isEmptyExtraction(data: AnalyzeResponse): boolean {
  const ocr = data.ocr_result;
  return (
    ocr.hospital_name.value === null &&
    ocr.patient_name.value === null &&
    ocr.total_amount.value === null &&
    ocr.line_items.filter((i) => !i.is_summary).length === 0
  );
}

export function useAnalyze(dispatch: React.Dispatch<WorkflowAction>) {
  const abortRef = useRef<AbortController | null>(null);

  const submit = useCallback(
    async (file: File, permissionToRecord: boolean) => {
      // Cancel any in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

      dispatch({ type: 'START_UPLOAD', file });

      try {
        let data = await analyzeDocument(file, permissionToRecord, controller.signal);

        // Auto-retry on empty extraction (GPU non-determinism can produce empty results)
        if (isEmptyExtraction(data)) {
          console.log('[Fee-Ver] Empty extraction, retrying automatically...');
          data = await analyzeDocument(file, permissionToRecord, controller.signal);
        }

        dispatch({ type: 'UPLOAD_SUCCESS', data });
      } catch (err) {
        if (controller.signal.aborted && !(err instanceof ApiRequestError)) {
          dispatch({
            type: 'UPLOAD_ERROR',
            error: {
              error: true,
              request_id: null,
              status_code: 504,
              error_type: 'inference_timeout',
              detail: 'Request timed out. The image may be too complex or the server is overloaded.',
              timestamp: new Date().toISOString(),
            },
          });
        } else if (err instanceof ApiRequestError) {
          dispatch({ type: 'UPLOAD_ERROR', error: err.apiError });
        } else {
          dispatch({
            type: 'UPLOAD_ERROR',
            error: {
              error: true,
              request_id: null,
              status_code: 0,
              error_type: 'network_error',
              detail: 'Could not connect to the analysis server. Check that the backend is running.',
              timestamp: new Date().toISOString(),
            } as ApiError,
          });
        }
      } finally {
        clearTimeout(timeout);
      }
    },
    [dispatch],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { submit, cancel };
}
