import { DuplicateAlert } from '../../shared/ui/DuplicateAlert';
import type { PaperImportBatch } from './api';

export function DuplicateReviewPanel({ batch }: { batch?: PaperImportBatch }) {
  if (!batch) return null;
  return (
    <section className="grid gap-3" aria-label="Duplicate review">
      <div className="grid gap-2 text-sm sm:grid-cols-3">
        <span>Accepted: {batch.acceptedCount}</span>
        <span>Duplicates: {batch.duplicateCount}</span>
        <span>Errors: {batch.errorCount}</span>
      </div>
      {batch.results
        .filter((result) => result.status === 'duplicate')
        .map((result, index) => (
          <DuplicateAlert key={index} reason={result.duplicateReason} message={result.message} />
        ))}
    </section>
  );
}
