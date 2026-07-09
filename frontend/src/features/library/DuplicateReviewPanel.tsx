import { Button } from '@/shared/ui/primitives/button';

import { useI18n } from '../i18n/I18nProvider';
import { usePaperImportReview, type PaperImportJob, type PaperRecord } from './api';

type DuplicateReviewPanelProps = {
  job?: PaperImportJob;
  isMaintainer?: boolean;
  onReviewed?: (job: PaperImportJob) => void;
  onSelectPaper?: (paper: PaperRecord) => void;
};

function paperTitle(paper: PaperRecord | null | undefined, fallback: string) {
  return paper ? paper.canonicalTitle || paper.title : fallback;
}

function basisText(value: string | undefined, noMatchLabel: string) {
  if (!value || value === 'none') return noMatchLabel;
  return value.replaceAll('_', ' ');
}

export function DuplicateReviewPanel({
  job,
  isMaintainer = false,
  onReviewed,
  onSelectPaper,
}: DuplicateReviewPanelProps) {
  const { t } = useI18n();
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
    <section className="grid gap-3 rounded-md border p-3 text-sm" aria-label={t('paperLibraryDuplicateReview')}>
      <div>
        <p className="font-semibold">
          {isDuplicate ? t('paperLibraryDuplicateDetected') : t('paperLibraryMaintainerReviewRequired')}
        </p>
        <p className="text-muted-foreground">
          {t('paperLibraryMatchBasis')} {basisText(detection.matchBasis, t('paperLibraryNoDuplicateMatch'))}
          {typeof detection.similarityScore === 'number'
            ? ` · ${t('paperLibrarySimilarity')} ${(detection.similarityScore * 100).toFixed(0)}%`
            : ''}
        </p>
      </div>
      {candidate ? (
        <div className="grid gap-2 rounded-md bg-muted p-3">
          <span className="font-medium">{paperTitle(candidate, t('paperLibraryCandidateUnavailable'))}</span>
          <span className="text-muted-foreground">
            {(candidate.authors ?? []).join(', ') || t('paperLibraryUnknownAuthors')}
          </span>
          <Button type="button" variant="secondary" onClick={() => onSelectPaper?.(candidate)}>
            {t('paperLibraryViewExistingPaper')}
          </Button>
        </div>
      ) : null}
      {isReview ? (
        <p role="status" className="text-muted-foreground">
          {t('paperLibraryReviewStatus')} {detection.reviewStatus.replaceAll('_', ' ')}
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
            {t('paperLibraryConfirmDuplicate')}
          </Button>
          <Button
            type="button"
            disabled={reviewMutation.isPending}
            onClick={() => review('confirm_distinct')}
          >
            {t('paperLibraryConfirmDistinct')}
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
