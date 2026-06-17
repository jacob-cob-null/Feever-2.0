'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

const STAGES = [
  { label: 'Preprocessing', description: 'Normalizing image to 1024×1024', duration: 3_000 },
  { label: 'OCR Inference', description: 'Vision model is reading your document', duration: 55_000 },
  { label: 'Cross-referencing', description: 'Matching against PhilHealth & hospital databases', duration: 8_000 },
  { label: 'Report', description: 'Building discrepancy analysis', duration: 5_000 },
];

const TOTAL_ESTIMATED = STAGES.reduce((sum, s) => sum + s.duration, 0);

export function StageIndicator({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed(Date.now() - startedAt), 200);
    return () => clearInterval(timer);
  }, [startedAt]);

  // Determine active stage
  let accumulated = 0;
  let activeIdx = 0;
  for (let i = 0; i < STAGES.length; i++) {
    if (elapsed > accumulated + STAGES[i].duration) {
      accumulated += STAGES[i].duration;
      activeIdx = Math.min(i + 1, STAGES.length - 1);
    } else {
      activeIdx = i;
      break;
    }
  }

  // Progress: smooth within each stage, caps at ~95% on last stage (we don't know when it truly finishes)
  let progress: number;
  if (activeIdx < STAGES.length - 1) {
    const stageElapsed = elapsed - accumulated;
    const stageProgress = Math.min(stageElapsed / STAGES[activeIdx].duration, 1);
    progress = ((accumulated + stageProgress * STAGES[activeIdx].duration) / TOTAL_ESTIMATED) * 100;
  } else {
    // Last stage: asymptotically approach 95%
    const stageElapsed = elapsed - accumulated;
    const asymptotic = 1 - Math.exp(-stageElapsed / 30_000);
    progress = ((accumulated / TOTAL_ESTIMATED) + (STAGES[activeIdx].duration / TOTAL_ESTIMATED) * asymptotic) * 100;
    progress = Math.min(progress, 95);
  }

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="h-1.5 w-full rounded-full bg-[var(--border-subtle)] overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-[var(--accent-indigo)]"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Stepper */}
      <div className="flex items-start justify-between gap-1">
        {STAGES.map((stage, i) => {
          const isDone = i < activeIdx;
          const isActive = i === activeIdx;

          return (
            <div key={stage.label} className="flex flex-col items-center flex-1 min-w-0">
              {/* Step dot/check */}
              <div
                className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-all duration-500 ${
                  isDone
                    ? 'bg-[var(--success)] text-white'
                    : isActive
                      ? 'bg-[var(--accent-indigo)] text-white shadow-[0_0_0_4px_var(--accent-indigo-subtle)]'
                      : 'bg-[var(--border-subtle)] text-[var(--text-tertiary)]'
                }`}
              >
                {isDone ? (
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>

              {/* Label */}
              <span
                className={`mt-2 text-xs font-medium text-center transition-colors duration-300 ${
                  isDone
                    ? 'text-[var(--success)]'
                    : isActive
                      ? 'text-[var(--text-primary)]'
                      : 'text-[var(--text-tertiary)]'
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Active stage description */}
      <motion.p
        key={activeIdx}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-sm text-[var(--text-secondary)] text-center"
      >
        {STAGES[activeIdx].description}
      </motion.p>
    </div>
  );
}
