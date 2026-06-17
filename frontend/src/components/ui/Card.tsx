'use client';

export function Card({
  children,
  className = '',
  borderColor,
}: {
  children: React.ReactNode;
  className?: string;
  borderColor?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] ${className}`}
      style={borderColor ? { borderLeftWidth: 3, borderLeftColor: borderColor } : undefined}
    >
      {children}
    </div>
  );
}

export function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <details open={defaultOpen} className="group">
      <summary className="flex cursor-pointer items-center gap-2 text-base font-semibold text-[var(--text-primary)] select-none list-none">
        <svg
          className="h-4 w-4 text-[var(--text-tertiary)] transition-transform group-open:rotate-90"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {title}
      </summary>
      <div className="mt-4">{children}</div>
    </details>
  );
}
