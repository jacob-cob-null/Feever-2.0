'use client';

import type { RuleEngineResult } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { CollapsibleSection } from '@/components/ui/Card';
import { formatPHP, formatPercent, formatMatchScore } from '@/lib/format';

const STATUS_VARIANT: Record<string, 'success' | 'high' | 'medium' | 'low' | 'neutral'> = {
  MATCH: 'success',
  WITHIN_LIMIT: 'success',
  DISCREPANCY: 'high',
  EXCEEDS_LIMIT: 'high',
  NOT_FOUND: 'medium',
  NOT_COVERED: 'low',
};

export function MatchPanel({ ruleEngine }: { ruleEngine: RuleEngineResult }) {
  return (
    <CollapsibleSection title="Match Details" defaultOpen={false}>
      <div className="space-y-6">
        {/* Hospital DB Matches */}
        <div>
          <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
            Hospital Database ({ruleEngine.hospital_db_matches.length} items)
          </h4>
          <div className="overflow-x-auto rounded-lg border border-[var(--border-subtle)]">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-gray-50/50">
                  <th className="px-3 py-2 text-left font-medium text-[var(--text-tertiary)]">Item</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--text-tertiary)]">Claimed</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--text-tertiary)]">Reference</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--text-tertiary)]">Delta</th>
                  <th className="px-3 py-2 text-center font-medium text-[var(--text-tertiary)]">Score</th>
                  <th className="px-3 py-2 text-center font-medium text-[var(--text-tertiary)]">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {ruleEngine.hospital_db_matches.map((m, i) => (
                  <tr key={`h-${i}`} className="hover:bg-[var(--bg-card-hover)]">
                    <td className="px-3 py-2 text-[var(--text-primary)] max-w-[200px] truncate">{m.item}</td>
                    <td className="px-3 py-2 text-right tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{formatPHP(m.claimed_amount)}</td>
                    <td className="px-3 py-2 text-right tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{formatPHP(m.reference_price)}</td>
                    <td className={`px-3 py-2 text-right tabular-nums ${m.delta_percent !== 0 ? 'text-[var(--severity-high)]' : 'text-[var(--text-tertiary)]'}`} style={{ fontFamily: 'var(--font-mono)' }}>
                      {formatPercent(m.delta_percent)}
                    </td>
                    <td className="px-3 py-2 text-center tabular-nums text-[var(--text-secondary)]">{formatMatchScore(m.match_score)}</td>
                    <td className="px-3 py-2 text-center">
                      <Badge variant={STATUS_VARIANT[m.status] || 'neutral'}>{m.status.replace('_', ' ')}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* PhilHealth Matches */}
        <div>
          <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
            PhilHealth Annex ({ruleEngine.philhealth_matches.length} items)
          </h4>
          <div className="overflow-x-auto rounded-lg border border-[var(--border-subtle)]">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-gray-50/50">
                  <th className="px-3 py-2 text-left font-medium text-[var(--text-tertiary)]">Item</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--text-tertiary)]">Claimed</th>
                  <th className="px-3 py-2 text-center font-medium text-[var(--text-tertiary)]">Annex</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--text-tertiary)]">Ceiling</th>
                  <th className="px-3 py-2 text-center font-medium text-[var(--text-tertiary)]">Score</th>
                  <th className="px-3 py-2 text-center font-medium text-[var(--text-tertiary)]">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {ruleEngine.philhealth_matches.map((m, i) => (
                  <tr key={`p-${i}`} className="hover:bg-[var(--bg-card-hover)]">
                    <td className="px-3 py-2 text-[var(--text-primary)] max-w-[200px] truncate">{m.item}</td>
                    <td className="px-3 py-2 text-right tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{formatPHP(m.claimed_amount)}</td>
                    <td className="px-3 py-2 text-center">
                      <Badge variant={m.annex_source === 'N/A' ? 'neutral' : 'indigo'}>{m.annex_source}</Badge>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{formatPHP(m.case_rate_ceiling)}</td>
                    <td className="px-3 py-2 text-center tabular-nums text-[var(--text-secondary)]">{formatMatchScore(m.match_score)}</td>
                    <td className="px-3 py-2 text-center">
                      <Badge variant={STATUS_VARIANT[m.status] || 'neutral'}>{m.status.replace(/_/g, ' ')}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </CollapsibleSection>
  );
}
