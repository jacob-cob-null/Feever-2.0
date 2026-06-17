'use client';

import type { ProcessingInfo } from '@/lib/types';
import { CollapsibleSection } from '@/components/ui/Card';
import { formatDuration } from '@/lib/format';

export function ProcessingMeta({ processing, defaultOpen = false }: { processing: ProcessingInfo; defaultOpen?: boolean }) {
  const rows: [string, string][] = [
    ['Total Time', formatDuration(processing.total_ms)],
    ['Normalization', formatDuration(processing.stages.normalization_ms)],
    ['Inference', formatDuration(processing.stages.inference_ms)],
    ['Rule Engine', formatDuration(processing.stages.rule_engine_ms)],
    ...(processing.stages.encryption_ms
      ? [['Encryption', formatDuration(processing.stages.encryption_ms)] as [string, string]]
      : []),
    ['Parse Tier', `Tier ${processing.parse_tier}${processing.parse_tier === 1 ? ' (clean)' : processing.parse_tier === 2 ? ' (repaired)' : ' (partial)'}`],
    ['Model', processing.model_version],
    ['Hospital Fuzzy Threshold', `${processing.thresholds_used.hospital_fuzzy}/100`],
    ['PhilHealth Fuzzy Threshold', `${processing.thresholds_used.philhealth_fuzzy}/100`],
    ['Price Delta Tolerance', `${(processing.thresholds_used.price_delta_tolerance * 100).toFixed(0)}%`],
  ];

  return (
    <CollapsibleSection title="Processing Details" defaultOpen={defaultOpen}>
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2">
          {rows.map(([label, value]) => (
            <div key={label} className="flex justify-between gap-4 py-1.5 border-b border-[var(--border-subtle)] last:border-b-0">
              <span className="text-xs text-[var(--text-tertiary)]">{label}</span>
              <span className="text-xs font-medium text-[var(--text-primary)] tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </CollapsibleSection>
  );
}
