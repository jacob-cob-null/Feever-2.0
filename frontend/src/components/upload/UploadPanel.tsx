'use client';

import { useState } from 'react';
import { DropZone } from './DropZone';
import { ImagePreview } from './ImagePreview';
import { ConsentToggle } from './ConsentToggle';
import { Button } from '@/components/ui/Button';

export function UploadPanel({
  onSubmit,
  isReady,
  isBusy,
}: {
  onSubmit: (file: File, permissionToRecord: boolean) => void;
  isReady: boolean;
  isBusy: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);

  const canSubmit = file && isReady && !isBusy;

  return (
    <div className="w-full max-w-xl mx-auto space-y-6">
      <DropZone onFile={setFile} disabled={!isReady || isBusy} />

      {file && <ImagePreview file={file} />}

      <ConsentToggle checked={consent} onChange={setConsent} />

      <div className="flex items-center gap-3">
        <Button
          disabled={!canSubmit}
          onClick={() => file && onSubmit(file, consent)}
          className="flex-1 py-3 text-base"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          Analyze Document
        </Button>
        {file && (
          <Button
            variant="ghost"
            onClick={() => setFile(null)}
            className="text-sm"
          >
            Clear
          </Button>
        )}
      </div>

      {!isReady && !isBusy && (
        <p className="text-center text-sm text-[var(--severity-high)]">
          Server is not available. Waiting for connection...
        </p>
      )}
      {isBusy && (
        <p className="text-center text-sm text-[var(--severity-medium)]">
          Another document is being processed. Please wait.
        </p>
      )}
    </div>
  );
}
