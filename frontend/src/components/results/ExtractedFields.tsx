'use client';

import type { OcrResult, ConfidenceField } from '@/lib/types';
import { ConfidenceBadge } from '@/components/ui/Badge';
import { CollapsibleSection } from '@/components/ui/Card';
import { formatPHP, formatDate } from '@/lib/format';

const FIELD_CONFIG: {
  key: keyof Omit<OcrResult, 'line_items'>;
  label: string;
  format?: (v: string | number) => string;
}[] = [
  { key: 'hospital_name', label: 'Hospital' },
  { key: 'patient_name', label: 'Patient' },
  { key: 'billing_date', label: 'Billing Date', format: (v) => formatDate(String(v)) },
  { key: 'total_amount', label: 'Total Amount', format: (v) => formatPHP(Number(v)) },
  { key: 'tax_amount', label: 'Tax Amount', format: (v) => formatPHP(Number(v)) },
  { key: 'philhealth_number', label: 'PhilHealth No.' },
  { key: 'diagnosis_code', label: 'Diagnosis Code (ICD-10)' },
  { key: 'procedure_code', label: 'Procedure Code (RVS)' },
  { key: 'philhealth_benefit', label: 'PhilHealth Benefit', format: (v) => formatPHP(Number(v)) },
  { key: 'balance_due', label: 'Balance Due', format: (v) => formatPHP(Number(v)) },
];

function FieldRow({ label, field, format }: { label: string; field: ConfidenceField; format?: (v: string | number) => string }) {
  const displayValue =
    field.value === null
      ? '—'
      : format
        ? format(field.value)
        : String(field.value);

  return (
    <div className="flex items-start justify-between gap-4 py-2.5 border-b border-[var(--border-subtle)] last:border-b-0">
      <span className="text-sm text-[var(--text-secondary)] flex-shrink-0">{label}</span>
      <div className="flex items-center gap-2 text-right">
        <span
          className={`text-sm font-medium ${field.value === null ? 'text-[var(--text-tertiary)]' : 'text-[var(--text-primary)]'}`}
          style={typeof field.value === 'number' ? { fontFamily: 'var(--font-mono)' } : undefined}
        >
          {displayValue}
        </span>
        <ConfidenceBadge confidence={field.confidence} />
      </div>
    </div>
  );
}

export function ExtractedFields({ ocr }: { ocr: OcrResult }) {
  return (
    <CollapsibleSection title="Extracted Data" defaultOpen={true}>
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-5">
        {FIELD_CONFIG.map((f) => (
          <FieldRow
            key={f.key}
            label={f.label}
            field={ocr[f.key] as ConfidenceField}
            format={f.format}
          />
        ))}
      </div>
    </CollapsibleSection>
  );
}
