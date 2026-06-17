'use client';

import { CollapsibleSection } from '@/components/ui/Card';

export function ExtractionNotes({ notes }: { notes: string[] }) {
  if (notes.length === 0) return null;

  return (
    <CollapsibleSection title="Extraction Notes" defaultOpen={false}>
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
        <ol className="space-y-2">
          {notes.map((note, i) => (
            <li key={i} className="flex gap-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              <span className="flex-shrink-0 text-xs text-[var(--text-tertiary)] tabular-nums mt-0.5" style={{ fontFamily: 'var(--font-mono)' }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              {note}
            </li>
          ))}
        </ol>
      </div>
    </CollapsibleSection>
  );
}
