'use client';

import { useEffect, useState } from 'react';
import { formatFileSize } from '@/lib/format';

export function ImagePreview({ file }: { file: File }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  return (
    <div className="flex items-start gap-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4 animate-fade-in">
      <div className="relative h-20 w-20 flex-shrink-0 overflow-hidden rounded-lg bg-gray-100">
        {url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={url}
            alt="Invoice preview"
            className="h-full w-full object-cover"
          />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-[var(--text-primary)]">
          {file.name}
        </p>
        <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
          {formatFileSize(file.size)} &middot; {file.type.split('/')[1]?.toUpperCase()}
        </p>
      </div>
    </div>
  );
}
