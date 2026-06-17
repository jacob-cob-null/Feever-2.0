'use client';

import { motion } from 'framer-motion';
import { StageIndicator } from './StageIndicator';
import { ImagePreview } from '@/components/upload/ImagePreview';
import { Button } from '@/components/ui/Button';

export function ProcessingView({
  file,
  startedAt,
  onCancel,
}: {
  file: File;
  startedAt: number;
  onCancel: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="w-full max-w-xl mx-auto space-y-8"
    >
      <div className="text-center">
        <h2
          className="text-2xl font-normal text-[var(--text-primary)]"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Analyzing your document
        </h2>
        <p className="mt-1 text-sm text-[var(--text-tertiary)]">
          This typically takes 1–2 minutes
        </p>
      </div>

      <ImagePreview file={file} />

      <StageIndicator startedAt={startedAt} />

      <div className="flex justify-center pt-2">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </motion.div>
  );
}
