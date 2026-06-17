'use client';

import { motion } from 'framer-motion';
import type { Discrepancy, Severity } from '@/lib/types';
import { DiscrepancyCard } from './DiscrepancyCard';

const SEVERITY_ORDER: Severity[] = ['HIGH', 'MEDIUM', 'LOW'];

export function DiscrepancyList({ discrepancies }: { discrepancies: Discrepancy[] }) {
  if (discrepancies.length === 0) return null;

  const grouped = SEVERITY_ORDER.map((severity) => ({
    severity,
    items: discrepancies.filter((d) => d.severity === severity),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-6">
      <h3
        className="text-lg text-[var(--text-primary)]"
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        Discrepancies
      </h3>
      {grouped.map((group) => (
        <div key={group.severity} className="space-y-3">
          {group.items.map((d, i) => (
            <motion.div
              key={`${d.item}-${d.violation}-${i}`}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
            >
              <DiscrepancyCard d={d} />
            </motion.div>
          ))}
        </div>
      ))}
    </div>
  );
}
