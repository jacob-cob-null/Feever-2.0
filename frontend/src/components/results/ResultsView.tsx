'use client';

import { motion } from 'framer-motion';
import type { AnalyzeResponse, OcrResult } from '@/lib/types';
import { VerdictBanner } from './VerdictBanner';
import { SummaryStats } from './SummaryStats';
import { DiscrepancyList } from './DiscrepancyList';
import { ExtractedFields } from './ExtractedFields';
import { LineItemsTable } from './LineItemsTable';
import { MatchPanel } from './MatchPanel';
import { ExtractionNotes } from './ExtractionNotes';
import { ProcessingMeta } from './ProcessingMeta';
import { Button } from '@/components/ui/Button';
import { formatTimestamp } from '@/lib/format';

export function ResultsView({
  data,
  onReset,
  onRetry,
}: {
  data: AnalyzeResponse;
  onReset: () => void;
  onRetry?: () => void;
}) {
  const ocr = data.ocr_result;
  const isSparse =
    ocr.hospital_name.value === null &&
    ocr.patient_name.value === null &&
    ocr.total_amount.value === null &&
    ocr.line_items.filter((i) => !i.is_summary).length === 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-4xl mx-auto space-y-8"
    >
      {/* Sparse extraction warning */}
      {isSparse && (
        <div className="rounded-xl border border-[var(--severity-medium-border)] bg-[var(--severity-medium-bg)] px-6 py-4">
          <p className="text-sm font-medium text-[var(--severity-medium)]">
            Extraction returned limited data
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            The model could not extract meaningful fields from this document. This can happen due to
            GPU non-determinism between inference runs. Re-analyzing the same image often produces
            better results.
          </p>
          <div className="mt-3 flex gap-3">
            {onRetry && (
              <Button variant="primary" onClick={onRetry} className="text-sm">
                Re-analyze this image
              </Button>
            )}
            <Button variant="ghost" onClick={onReset} className="text-sm">
              Upload a different image
            </Button>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1
            className="text-3xl text-[var(--text-primary)]"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Analysis Report
          </h1>
          <p className="mt-1 text-sm text-[var(--text-tertiary)]">
            {formatTimestamp(data.timestamp)} &middot; {data.request_id.slice(0, 8)}
          </p>
        </div>
        <Button variant="secondary" onClick={onReset}>
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Analyze Another
        </Button>
      </div>

      {/* 1. Verdict */}
      <VerdictBanner summary={data.summary} discrepancies={data.discrepancies} />

      {/* 2. Summary Stats */}
      <SummaryStats summary={data.summary} />

      {/* 3. Discrepancies */}
      <DiscrepancyList discrepancies={data.discrepancies} />

      {/* 4. Extracted Data */}
      <ExtractedFields ocr={data.ocr_result} />

      {/* 5. Line Items */}
      <LineItemsTable
        items={data.ocr_result.line_items}
        hospitalMatches={data.rule_engine.hospital_db_matches}
        philhealthMatches={data.rule_engine.philhealth_matches}
      />

      {/* 6. Match Details */}
      <MatchPanel ruleEngine={data.rule_engine} />

      {/* 7. Extraction Notes */}
      <ExtractionNotes notes={data.extraction_notes} />

      {/* 8. Processing Details — open by default if extraction was sparse */}
      <ProcessingMeta processing={data.processing} defaultOpen={isSparse} />

      {/* Footer */}
      <div className="border-t border-[var(--border-subtle)] pt-6 pb-8 text-center">
        <p className="text-xs text-[var(--text-tertiary)]">
          {data.recorded ? 'This analysis was recorded and encrypted.' : 'This analysis was not recorded.'}
          {' '}&middot;{' '}
          Model: {data.processing.model_version}
        </p>
      </div>
    </motion.div>
  );
}
