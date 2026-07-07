import { FolderOpen } from 'lucide-react';
import { useRef, useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';

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
  const [files, setFiles] = useState<File[]>([]);
  const [jobs, setJobs] = useState<PaperImportJob[]>([]);
  const [uploadError, setUploadError] = useState<string | undefined>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const importMutation = useSharedPaperPdfImport();
  const uploadPolicyQuery = usePaperUploadPolicy();
  const maxSizeLabel = uploadPolicyQuery.data?.displayLabel ?? t('paperLibraryLoadingPolicy');
  const latestJob = jobs.at(-1);
  const reviewJob = [...jobs]
    .reverse()
    .find((item) => item.status === 'duplicate' || item.status === 'maintainer_review');
  const selectedFileSummary =
    files.length === 1
      ? `${t('paperLibrarySelectedPdfPrefix')} ${files[0].name}`
      : files.length > 1
        ? `${files.length} ${t('paperLibrarySelectedPdfsSuffix')}`
        : '';
  const currentStatus = importMutation.isPending
    ? t('paperLibraryProcessingPdf')
    : statusText(latestJob, t) || selectedFileSummary;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!files.length) return;
    const oversized = files.find(
      (selectedFile) =>
        uploadPolicyQuery.data?.maxSizeBytes &&
        selectedFile.size > uploadPolicyQuery.data.maxSizeBytes,
    );
    if (oversized) {
      setUploadError(
        `${oversized.name}: ${t('paperLibraryUploadLimitExceededPrefix')} ${uploadPolicyQuery.data?.displayLabel} ${t(
          'paperLibraryUploadLimitExceededSuffix',
        )}`,
      );
      return;
    }
    setUploadError(undefined);
    setJobs([]);
    const importedJobs: PaperImportJob[] = [];
    const failedFiles: File[] = [];
    const failedMessages: string[] = [];
    for (const selectedFile of files) {
      try {
        const result = await importMutation.mutateAsync(selectedFile);
        importedJobs.push(result);
        setJobs([...importedJobs]);
        if (result.status === 'rejected' || result.status === 'failed') {
          failedFiles.push(selectedFile);
          failedMessages.push(`${selectedFile.name}: ${statusText(result, t)}`);
          continue;
        }
        if (result.status === 'accepted' && result.acceptedPaper) {
          onAccepted?.(result.acceptedPaper);
        }
        if (result.status === 'duplicate' && result.duplicatePaper) {
          onSelectPaper?.(result.duplicatePaper);
        }
      } catch (err) {
        const message = err && typeof err === 'object' && 'message' in err ? String(err.message) : t('paperLibraryProcessingFailed');
        failedFiles.push(selectedFile);
        failedMessages.push(`${selectedFile.name}: ${message}`);
      }
    }
    setUploadError(failedMessages.length ? failedMessages.join(' ') : undefined);
    if (failedFiles.length) {
      setFiles(failedFiles);
    } else {
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  return (
    <form
      className="grid min-w-0 gap-3 overflow-hidden rounded-md border p-3"
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
      <div className="grid min-w-0 gap-2">
        <input
          id="paper-pdf-file-input"
          ref={fileInputRef}
          className="hidden"
          aria-label={t('paperLibraryPdfFile')}
          name="file"
          type="file"
          accept="application/pdf,.pdf"
          multiple
          onChange={(event) => {
            setFiles(Array.from(event.target.files ?? []));
            setJobs([]);
            setUploadError(undefined);
          }}
        />
        <Button
          type="button"
          variant="outline"
          className="min-w-0"
          onClick={() => {
            if (fileInputRef.current) fileInputRef.current.value = '';
            fileInputRef.current?.click();
          }}
          aria-label={t('paperLibraryChoosePdfs')}
        >
          <FolderOpen className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span className="truncate">{t('paperLibraryChoosePdfs')}</span>
        </Button>
        {files.length ? (
          <ul className="max-h-24 min-w-0 max-w-full overflow-y-auto rounded-md border bg-muted/20 p-2 text-xs text-muted-foreground" aria-label={t('paperLibrarySelectedFiles')}>
            {files.map((selectedFile) => (
              <li key={`${selectedFile.name}-${selectedFile.size}`} className="block min-w-0 max-w-full truncate" title={selectedFile.name}>
                {selectedFile.name}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      <Button type="submit" className="min-w-0" disabled={!files.length || importMutation.isPending}>
        {files.length > 1 ? t('paperLibraryImportPdfsButton') : t('paperLibraryImportPdfButton')}
      </Button>
      {importMutation.isPending ? <UploadProgress label={t('paperLibraryProcessingPdf')} value={65} /> : null}
      {uploadError || importMutation.error ? (
        <p role="alert" className="min-w-0 break-words text-sm font-medium text-destructive">
          {uploadError ?? importMutation.error?.message}
        </p>
      ) : null}
      {currentStatus ? (
        <p
          id="paper-import-status"
          role="status"
          aria-live="polite"
          className="min-w-0 break-words text-sm font-medium text-success"
        >
          {currentStatus}
        </p>
      ) : null}
      <DuplicateReviewPanel
        job={reviewJob}
        isMaintainer={isMaintainer}
        onSelectPaper={onSelectPaper}
        onReviewed={(reviewedJob) => {
          setJobs((current) =>
            current.map((item) => (item.id === reviewedJob.id ? reviewedJob : item)),
          );
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
