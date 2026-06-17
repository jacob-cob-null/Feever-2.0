'use client';

import type { Severity } from '@/lib/types';

type BadgeVariant = 'high' | 'medium' | 'low' | 'success' | 'neutral' | 'indigo';

const variantStyles: Record<BadgeVariant, string> = {
  high: 'bg-[var(--severity-high-bg)] text-[var(--severity-high)] border-[var(--severity-high-border)]',
  medium: 'bg-[var(--severity-medium-bg)] text-[var(--severity-medium)] border-[var(--severity-medium-border)]',
  low: 'bg-[var(--severity-low-bg)] text-[var(--severity-low)] border-[var(--severity-low-border)]',
  success: 'bg-[var(--success-bg)] text-[var(--success)] border-emerald-200',
  neutral: 'bg-gray-50 text-[var(--text-secondary)] border-gray-200',
  indigo: 'bg-[var(--accent-indigo-subtle)] text-[var(--accent-indigo)] border-indigo-200',
};

export function Badge({
  children,
  variant = 'neutral',
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium tracking-wide uppercase ${variantStyles[variant]}`}
    >
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const variant: BadgeVariant = severity === 'HIGH' ? 'high' : severity === 'MEDIUM' ? 'medium' : 'low';
  return <Badge variant={variant}>{severity}</Badge>;
}

export function ConfidenceBadge({ confidence }: { confidence: 'high' | 'medium' | 'low' | null }) {
  if (!confidence) return <Badge variant="neutral">Not found</Badge>;
  const variant: BadgeVariant = confidence === 'high' ? 'success' : confidence === 'medium' ? 'medium' : 'high';
  return <Badge variant={variant}>{confidence}</Badge>;
}
