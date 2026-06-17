'use client';

import { motion } from 'framer-motion';
import type { Summary } from '@/lib/types';
import { formatPHP } from '@/lib/format';

interface StatItem {
  label: string;
  value: string;
  highlight?: boolean;
}

export function SummaryStats({ summary }: { summary: Summary }) {
  const stats: StatItem[] = [
    { label: 'Total Claimed', value: formatPHP(summary.total_claimed) },
    { label: 'Total Allowable', value: formatPHP(summary.total_allowable) },
    {
      label: 'Excess Amount',
      value: formatPHP(summary.excess_amount),
      highlight: summary.excess_amount > 0,
    },
    { label: 'Items Flagged', value: `${summary.items_flagged} / ${summary.total_items}`, highlight: summary.items_flagged > 0 },
    { label: 'Items Matched', value: `${summary.items_matched} / ${summary.total_items}` },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: i * 0.06 }}
          className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
        >
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
            {stat.label}
          </p>
          <p
            className={`mt-1.5 text-lg font-semibold tabular-nums ${
              stat.highlight ? 'text-[var(--severity-high)]' : 'text-[var(--text-primary)]'
            }`}
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            {stat.value}
          </p>
        </motion.div>
      ))}
    </div>
  );
}
