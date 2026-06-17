import type { AnalyzeResponse, ApiError, HealthResponse } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiRequestError extends Error {
  constructor(public apiError: ApiError) {
    super(apiError.detail);
    this.name = 'ApiRequestError';
  }
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/health`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

export async function analyzeDocument(
  file: File,
  permissionToRecord: boolean,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('permission_to_record', String(permissionToRecord));

  const res = await fetch(`${API_URL}/analyze`, {
    method: 'POST',
    body: formData,
    signal,
  });

  const data = await res.json();

  console.log('[Fee-Ver] Response status:', res.status);
  console.log('[Fee-Ver] Inference ms:', data.processing?.stages?.inference_ms);
  console.log('[Fee-Ver] Parse tier:', data.processing?.parse_tier);
  console.log('[Fee-Ver] Line items:', data.ocr_result?.line_items?.length);
  console.log('[Fee-Ver] Full response:', data);

  if (!res.ok || data.error) {
    throw new ApiRequestError(data as ApiError);
  }

  return data as AnalyzeResponse;
}
