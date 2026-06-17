'use client';

import { useCallback, useRef, useState } from 'react';
import { formatFileSize } from '@/lib/format';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

export function DropZone({
  onFile,
  disabled,
}: {
  onFile: (file: File) => void;
  disabled: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback((file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return `Unsupported format. Use JPG, PNG, or WebP.`;
    }
    if (file.size > MAX_SIZE) {
      return `File too large (${formatFileSize(file.size)}). Maximum is 10 MB.`;
    }
    return null;
  }, []);

  const handleFile = useCallback(
    (file: File) => {
      const err = validate(file);
      if (err) {
        setError(err);
        return;
      }
      setError(null);
      onFile(file);
    },
    [onFile, validate],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [disabled, handleFile],
  );

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`
          relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-12 transition-all duration-200 cursor-pointer
          ${disabled ? 'opacity-40 cursor-not-allowed' : ''}
          ${
            dragging
              ? 'border-[var(--accent-indigo)] bg-[var(--accent-indigo-subtle)] scale-[1.01]'
              : 'border-[var(--border-medium)] hover:border-[var(--accent-indigo)] hover:bg-[var(--accent-indigo-subtle)]/30'
          }
        `}
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-[var(--accent-indigo-subtle)]">
          <svg className="h-7 w-7 text-[var(--accent-indigo)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </div>
        <div className="text-center">
          <p className="text-base font-medium text-[var(--text-primary)]">
            Drop your hospital invoice here
          </p>
          <p className="mt-1 text-sm text-[var(--text-tertiary)]">
            or click to browse &middot; JPG, PNG, WebP &middot; max 10 MB
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.webp"
          className="hidden"
          disabled={disabled}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = '';
          }}
        />
      </div>
      {error && (
        <p className="mt-3 text-sm text-[var(--severity-high)] animate-fade-in">
          {error}
        </p>
      )}
    </div>
  );
}
