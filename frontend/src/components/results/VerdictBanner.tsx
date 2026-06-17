'use client';

import { motion } from 'framer-motion';
import type { Summary, Discrepancy } from '@/lib/types';
import { formatPHP } from '@/lib/format';

export function VerdictBanner({
  summary,
  discrepancies,
}: {
  summary: Summary;
  discrepancies: Discrepancy[];
}) {
  const highCount = discrepancies.filter((d) => d.severity === 'HIGH').length;
  const mediumCount = discrepancies.filter((d) => d.severity === 'MEDIUM').length;
  const hasIssues = discrepancies.length > 0;

  let bgClass: string;
  let borderClass: string;
  let textClass: string;
  let heading: string;
  let sub: string;

  if (highCount > 0) {
    bgClass = 'bg-[var(--severity-high-bg)]';
    borderClass = 'border-[var(--severity-high)]';
    textClass = 'text-[var(--severity-high)]';
    heading = `${highCount} critical issue${highCount > 1 ? 's' : ''} found`;
    sub = `${discrepancies.length} total discrepancies across ${summary.total_items} line items`;
  } else if (mediumCount > 0) {
    bgClass = 'bg-[var(--severity-medium-bg)]';
    borderClass = 'border-[var(--severity-medium)]';
    textClass = 'text-[var(--severity-medium)]';
    heading = `${mediumCount} issue${mediumCount > 1 ? 's' : ''} require attention`;
    sub = `${discrepancies.length} total discrepancies across ${summary.total_items} line items`;
  } else if (hasIssues) {
    bgClass = 'bg-[var(--severity-low-bg)]';
    borderClass = 'border-[var(--severity-low)]';
    textClass = 'text-[var(--severity-low)]';
    heading = `${discrepancies.length} low-priority note${discrepancies.length > 1 ? 's' : ''}`;
    sub = `No critical issues found across ${summary.total_items} line items`;
  } else {
    bgClass = 'bg-[var(--success-bg)]';
    borderClass = 'border-[var(--success)]';
    textClass = 'text-[var(--success)]';
    heading = 'No discrepancies found';
    sub = `All ${summary.total_items} line items verified against reference databases`;
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className={`rounded-2xl border-l-4 ${borderClass} ${bgClass} px-8 py-6`}
    >
      <h2
        className={`text-2xl ${textClass}`}
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        {heading}
      </h2>
      <p className="mt-1 text-sm text-[var(--text-secondary)]">{sub}</p>
      {summary.excess_amount > 0 && (
        <p className="mt-3 text-lg font-medium text-[var(--severity-high)]" style={{ fontFamily: 'var(--font-mono)' }}>
          Excess: {formatPHP(summary.excess_amount)}
        </p>
      )}
    </motion.div>
  );
}
