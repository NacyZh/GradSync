import { Button } from '@/components/ui/button';

import { usePaperImportReview, type PaperImportJob, type PaperRecord } from './api';

type DuplicateReviewPanelProps = {
  job?: PaperImportJob;
  isMaintainer?: boolean;
  onReviewed?: (job: PaperImportJob) => void;
  onSelectPaper?: (paper: PaperRecord) => void;
};

function paperTitle(paper?: PaperRecord | null) {
  return paper ? paper.canonicalTitle || paper.title : 'Candidate paper unavailable';
}

function basisText(value?: string) {
  if (!value || value === 'none') return 'No duplicate match';
  return value.replaceAll('_', ' ');
}

export function DuplicateReviewPanel({
  job,
  isMaintainer = false,
  onReviewed,
  onSelectPaper,
}: DuplicateReviewPanelProps) {
  const reviewMutation = usePaperImportReview();
  if (!job || !job.duplicateDetection) return null;

  const detection = job.duplicateDetection;
  const candidate = job.duplicatePaper;
  const isReview = job.status === 'maintainer_review';
  const isDuplicate = job.status === 'duplicate';

  async function review(decision: 'confirm_duplicate' | 'confirm_distinct') {
    if (!job) return;
    const result = await reviewMutation.mutateAsync({ importJobId: job.id, decision });
    onReviewed?.(result);
  }

  return (
    <section className="grid gap-3 rounded-md border p-3 text-sm" aria-label="Duplicate review">
      <div>
        <p className="font-semibold">
          {isDuplicate ? 'Duplicate paper detected' : 'Maintainer review required'}
        </p>
        <p className="text-muted-foreground">
          Match basis: {basisText(detection.matchBasis)}
          {typeof detection.similarityScore === 'number'
            ? ` · Similarity ${(detection.similarityScore * 100).toFixed(0)}%`
            : ''}
        </p>
      </div>
      {candidate ? (
        <div className="grid gap-2 rounded-md bg-muted p-3">
          <span className="font-medium">{paperTitle(candidate)}</span>
          <span className="text-muted-foreground">
            {(candidate.authors ?? []).join(', ') || 'Unknown authors'}
          </span>
          <Button type="button" variant="secondary" onClick={() => onSelectPaper?.(candidate)}>
            View existing paper
          </Button>
        </div>
      ) : null}
      {isReview ? (
        <p role="status" className="text-muted-foreground">
          Review status: {detection.reviewStatus.replaceAll('_', ' ')}
        </p>
      ) : null}
      {isReview && isMaintainer ? (
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={reviewMutation.isPending}
            onClick={() => review('confirm_duplicate')}
          >
            Confirm duplicate
          </Button>
          <Button
            type="button"
            disabled={reviewMutation.isPending}
            onClick={() => review('confirm_distinct')}
          >
            Confirm distinct
          </Button>
        </div>
      ) : null}
      {reviewMutation.error ? (
        <p role="alert" className="font-medium text-destructive">
          {reviewMutation.error.message}
        </p>
      ) : null}
    </section>
  );
}
