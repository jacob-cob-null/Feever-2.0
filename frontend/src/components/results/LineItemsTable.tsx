'use client';

import type { LineItem, HospitalDbMatch, PhilhealthMatch } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { CollapsibleSection } from '@/components/ui/Card';
import { formatPHP } from '@/lib/format';

function getHospitalStatus(item: string, matches: HospitalDbMatch[]) {
  return matches.find((m) => m.item === item);
}

function getPhilhealthStatus(item: string, matches: PhilhealthMatch[]) {
  return matches.find((m) => m.item === item);
}

const STATUS_VARIANT: Record<string, 'success' | 'high' | 'medium' | 'low' | 'neutral'> = {
  MATCH: 'success',
  WITHIN_LIMIT: 'success',
  DISCREPANCY: 'high',
  EXCEEDS_LIMIT: 'high',
  NOT_FOUND: 'medium',
  NOT_COVERED: 'low',
};

export function LineItemsTable({
  items,
  hospitalMatches,
  philhealthMatches,
}: {
  items: LineItem[];
  hospitalMatches: HospitalDbMatch[];
  philhealthMatches: PhilhealthMatch[];
}) {
  const billableItems = items.filter((i) => !i.is_summary);
  const summaryItems = items.filter((i) => i.is_summary);

  return (
    <CollapsibleSection title={`Line Items (${billableItems.length} billable)`} defaultOpen={true}>
      <div className="overflow-x-auto rounded-xl border border-[var(--border-subtle)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-subtle)] bg-gray-50/50">
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                Description
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                Qty
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                Price
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                Hospital DB
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                PhilHealth
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-subtle)]">
            {billableItems.map((item, i) => {
              const hospital = getHospitalStatus(item.description, hospitalMatches);
              const philhealth = getPhilhealthStatus(item.description, philhealthMatches);

              return (
                <tr
                  key={`${item.description}-${i}`}
                  className="hover:bg-[var(--bg-card-hover)] transition-colors"
                >
                  <td className="px-4 py-3 text-[var(--text-primary)] max-w-xs truncate">
                    {item.description}
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--text-secondary)] tabular-nums">
                    {item.quantity ?? '—'}
                  </td>
                  <td
                    className="px-4 py-3 text-right text-[var(--text-primary)] font-medium tabular-nums"
                    style={{ fontFamily: 'var(--font-mono)' }}
                  >
                    {item.price !== null ? formatPHP(item.price) : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {hospital ? (
                      <Badge variant={STATUS_VARIANT[hospital.status] || 'neutral'}>
                        {hospital.status.replace('_', ' ')}
                      </Badge>
                    ) : (
                      <span className="text-[var(--text-tertiary)]">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {philhealth ? (
                      <Badge variant={STATUS_VARIANT[philhealth.status] || 'neutral'}>
                        {philhealth.status.replace('_', ' ')}
                      </Badge>
                    ) : (
                      <span className="text-[var(--text-tertiary)]">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {summaryItems.length > 0 && (
        <p className="mt-2 text-xs text-[var(--text-tertiary)]">
          {summaryItems.length} summary field{summaryItems.length > 1 ? 's' : ''} excluded from matching:{' '}
          {summaryItems.map((s) => s.description).join(', ')}
        </p>
      )}
    </CollapsibleSection>
  );
}
