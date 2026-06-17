'use client';

export function ConsentToggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer select-none group">
      <div className="relative mt-0.5">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <div
          className={`h-5 w-9 rounded-full transition-colors duration-200 ${
            checked ? 'bg-[var(--accent-indigo)]' : 'bg-[var(--border-medium)]'
          }`}
        />
        <div
          className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform duration-200 ${
            checked ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </div>
      <div>
        <p className="text-sm font-medium text-[var(--text-primary)] group-hover:text-[var(--accent-indigo)] transition-colors">
          Allow recording for quality review
        </p>
        <p className="text-xs text-[var(--text-tertiary)] leading-relaxed mt-0.5">
          Encrypts and saves this analysis (AES-256-GCM). Includes raw OCR text in results.
          Compliant with RA 10173.
        </p>
      </div>
    </label>
  );
}
