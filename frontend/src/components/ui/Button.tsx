'use client';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--accent-indigo)] text-white hover:bg-[var(--accent-indigo-light)] active:scale-[0.98] shadow-sm',
  secondary:
    'bg-white text-[var(--text-primary)] border border-[var(--border-subtle)] hover:bg-[var(--bg-card-hover)] active:scale-[0.98]',
  ghost:
    'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)]',
};

export function Button({
  children,
  variant = 'primary',
  disabled,
  className = '',
  ...props
}: {
  children: React.ReactNode;
  variant?: ButtonVariant;
  disabled?: boolean;
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100 ${variantStyles[variant]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
