import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { DuplicateReviewPanel } from './DuplicateReviewPanel';
import { useSharedPaperPdfImport, type PaperImportJob, type PaperRecord } from './api';

type PaperImportPanelProps = {
  onAccepted?: (paper: PaperRecord) => void;
  onSelectPaper?: (paper: PaperRecord) => void;
  isMaintainer?: boolean;
};

function statusText(job?: PaperImportJob) {
  if (!job) return '';
  if (job.status === 'accepted' && job.acceptedPaper) {
    return `Accepted: ${job.acceptedPaper.canonicalTitle || job.acceptedPaper.title}`;
  }
  if (job.status === 'duplicate' && job.duplicatePaper) {
    return `Duplicate: ${job.duplicatePaper.canonicalTitle || job.duplicatePaper.title}`;
  }
  if (job.status === 'maintainer_review') {
    return 'Maintainer review required';
  }
  if (job.status === 'rejected') {
    return `Rejected: ${job.failureReason || job.userMessage || 'Upload rejected'}`;
  }
  if (job.status === 'failed') {
    return `Failed: ${job.failureReason || job.userMessage || 'Processing failed'}`;
  }
  return job.userMessage || job.status.replaceAll('_', ' ');
}

export function PaperImportPanel({ onAccepted, onSelectPaper, isMaintainer = false }: PaperImportPanelProps) {
  const [file, setFile] = useState<File | undefined>();
  const [job, setJob] = useState<PaperImportJob | undefined>();
  const importMutation = useSharedPaperPdfImport();
  const currentStatus = importMutation.isPending
    ? 'Processing PDF'
    : statusText(job) || (file ? `Selected PDF: ${file.name}` : '');

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setJob(undefined);
    const result = await importMutation.mutateAsync(file);
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
      <UploadRequirements title="Import paper PDF" extensions={['.pdf']} maxSizeLabel="25 MB" />
      <Input
        aria-label="PDF file"
        name="file"
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => {
          setFile(event.target.files?.[0]);
          setJob(undefined);
        }}
        required
      />
      <Button type="submit" disabled={!file || importMutation.isPending}>
        Import PDF
      </Button>
      {importMutation.isPending ? <UploadProgress label="Processing PDF" value={65} /> : null}
      {importMutation.error ? (
        <p role="alert" className="text-sm font-medium text-destructive">
          {importMutation.error.message}
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
