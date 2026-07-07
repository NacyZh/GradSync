import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { useI18n } from '../i18n/I18nProvider';
import { DuplicateReviewPanel } from './DuplicateReviewPanel';
import { usePaperUploadPolicy, useSharedPaperPdfImport, type PaperImportJob, type PaperRecord } from './api';

type PaperImportPanelProps = {
  onAccepted?: (paper: PaperRecord) => void;
  onSelectPaper?: (paper: PaperRecord) => void;
  isMaintainer?: boolean;
};

type PaperLibraryT = ReturnType<typeof useI18n>['t'];

function statusText(job: PaperImportJob | undefined, t: PaperLibraryT) {
  if (!job) return '';
  if (job.status === 'accepted' && job.acceptedPaper) {
    return `${t('paperLibraryAcceptedPrefix')} ${job.acceptedPaper.canonicalTitle || job.acceptedPaper.title}`;
  }
  if (job.status === 'duplicate' && job.duplicatePaper) {
    return `${t('paperLibraryDuplicatePrefix')} ${job.duplicatePaper.canonicalTitle || job.duplicatePaper.title}`;
  }
  if (job.status === 'maintainer_review') {
    return t('paperLibraryMaintainerReviewRequired');
  }
  if (job.status === 'rejected') {
    return `${t('paperLibraryRejectedPrefix')} ${job.failureReason || job.userMessage || t('paperLibraryUploadRejected')}`;
  }
  if (job.status === 'failed') {
    return `${t('paperLibraryFailedPrefix')} ${job.failureReason || job.userMessage || t('paperLibraryProcessingFailed')}`;
  }
  return job.userMessage || job.status.replaceAll('_', ' ');
}

export function PaperImportPanel({ onAccepted, onSelectPaper, isMaintainer = false }: PaperImportPanelProps) {
  const { t } = useI18n();
  const [file, setFile] = useState<File | undefined>();
  const [job, setJob] = useState<PaperImportJob | undefined>();
  const [uploadError, setUploadError] = useState<string | undefined>();
  const importMutation = useSharedPaperPdfImport();
  const uploadPolicyQuery = usePaperUploadPolicy();
  const maxSizeLabel = uploadPolicyQuery.data?.displayLabel ?? t('paperLibraryLoadingPolicy');
  const currentStatus = importMutation.isPending
    ? t('paperLibraryProcessingPdf')
    : statusText(job, t) || (file ? `${t('paperLibrarySelectedPdfPrefix')} ${file.name}` : '');

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    if (uploadPolicyQuery.data?.maxSizeBytes && file.size > uploadPolicyQuery.data.maxSizeBytes) {
      setUploadError(
        `${t('paperLibraryUploadLimitExceededPrefix')} ${uploadPolicyQuery.data.displayLabel} ${t(
          'paperLibraryUploadLimitExceededSuffix',
        )}`,
      );
      return;
    }
    setUploadError(undefined);
    setJob(undefined);
    const result = await importMutation.mutateAsync(file).catch(() => undefined);
    if (!result) return;
    setJob(result);
    if (result.status === 'accepted' && result.acceptedPaper) {
      onAccepted?.(result.acceptedPaper);
      setFile(undefined);
    }
    if (result.status === 'duplicate' && result.duplicatePaper) {
      onSelectPaper?.(result.duplicatePaper);
      setFile(undefined);
    }
  }

  return (
    <form
      className="grid gap-3 rounded-md border p-3"
      onSubmit={onSubmit}
      aria-describedby="paper-import-status"
      noValidate
    >
      <UploadRequirements
        title={t('paperLibraryImportPdf')}
        extensions={uploadPolicyQuery.data?.allowedExtensions ?? ['.pdf']}
        maxSizeLabel={maxSizeLabel}
        description={`${(uploadPolicyQuery.data?.allowedExtensions ?? ['.pdf']).join(', ')} ${t('paperLibraryUpTo')} ${maxSizeLabel}`}
      />
      <Input
        aria-label={t('paperLibraryPdfFile')}
        name="file"
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => {
          setFile(event.target.files?.[0]);
          setJob(undefined);
          setUploadError(undefined);
        }}
        required
      />
      <Button type="submit" disabled={!file || importMutation.isPending}>
        {t('paperLibraryImportPdfButton')}
      </Button>
      {importMutation.isPending ? <UploadProgress label={t('paperLibraryProcessingPdf')} value={65} /> : null}
      {uploadError || importMutation.error ? (
        <p role="alert" className="text-sm font-medium text-destructive">
          {uploadError ?? importMutation.error?.message}
        </p>
      ) : null}
      {currentStatus ? (
        <p
          id="paper-import-status"
          role="status"
          aria-live="polite"
          className="text-sm font-medium text-success"
        >
          {currentStatus}
        </p>
      ) : null}
      <DuplicateReviewPanel
        job={job}
        isMaintainer={isMaintainer}
        onSelectPaper={onSelectPaper}
        onReviewed={(reviewedJob) => {
          setJob(reviewedJob);
          if (reviewedJob.status === 'accepted' && reviewedJob.acceptedPaper) {
            onAccepted?.(reviewedJob.acceptedPaper);
          }
          if (reviewedJob.status === 'duplicate' && reviewedJob.duplicatePaper) {
            onSelectPaper?.(reviewedJob.duplicatePaper);
          }
        }}
      />
    </form>
  );
}
