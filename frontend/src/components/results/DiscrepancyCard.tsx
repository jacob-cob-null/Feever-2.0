'use client';

import type { Discrepancy } from '@/lib/types';
import { SeverityBadge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { formatPHP } from '@/lib/format';

const SEVERITY_COLORS: Record<string, string> = {
  HIGH: 'var(--severity-high)',
  MEDIUM: 'var(--severity-medium)',
  LOW: 'var(--severity-low)',
};

const VIOLATION_LABELS: Record<string, string> = {
  EXCEEDS_PHILHEALTH_CEILING: 'Exceeds PhilHealth Ceiling',
  PRICE_MISMATCH: 'Price Mismatch',
  NOT_IN_HOSPITAL_SCHEDULE: 'Not in Hospital Schedule',
  NOT_COVERED: 'Not PhilHealth Covered',
};

export function DiscrepancyCard({ d }: { d: Discrepancy }) {
  return (
    <Card borderColor={SEVERITY_COLORS[d.severity]}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={d.severity} />
          <span className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wide">
            {VIOLATION_LABELS[d.violation] || d.violation}
          </span>
        </div>
        <span
          className="text-sm font-semibold text-[var(--text-primary)] tabular-nums"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          {formatPHP(d.claimed_amount)}
        </span>
      </div>

      <h4 className="mt-3 text-sm font-semibold text-[var(--text-primary)]">
        {d.item}
      </h4>

      <p className="mt-1.5 text-sm leading-relaxed text-[var(--text-secondary)]">
        {d.detail}
      </p>

      {d.reviewer_action && (
        <div className="mt-3 rounded-lg bg-[var(--accent-indigo-subtle)] px-3 py-2.5">
          <p className="text-xs font-medium text-[var(--accent-indigo)] uppercase tracking-wide mb-1">
            Reviewer Action
          </p>
          <p className="text-sm text-[var(--accent-indigo)] leading-relaxed">
            {d.reviewer_action}
          </p>
        </div>
      )}

      {(d.reference_code || d.reference_source) && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-[var(--text-tertiary)]">
          {d.reference_code && (
            <span className="rounded bg-gray-50 px-2 py-0.5 border border-gray-100" style={{ fontFamily: 'var(--font-mono)' }}>
              {d.reference_code}
            </span>
          )}
          {d.reference_source && (
            <span className="rounded bg-gray-50 px-2 py-0.5 border border-gray-100">
              {d.reference_source}
            </span>
          )}
        </div>
      )}
    </Card>
  );
}
