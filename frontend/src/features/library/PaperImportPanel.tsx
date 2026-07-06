import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { useSharedPaperPdfImport, type PaperImportJob, type PaperRecord } from './api';

type PaperImportPanelProps = {
  onAccepted?: (paper: PaperRecord) => void;
};

function statusText(job?: PaperImportJob) {
  if (!job) return '';
  if (job.status === 'accepted' && job.acceptedPaper) {
    return `Accepted: ${job.acceptedPaper.canonicalTitle || job.acceptedPaper.title}`;
  }
  if (job.status === 'rejected') {
    return `Rejected: ${job.failureReason || job.userMessage || 'Upload rejected'}`;
  }
  if (job.status === 'failed') {
    return `Failed: ${job.failureReason || job.userMessage || 'Processing failed'}`;
  }
  return job.userMessage || job.status.replaceAll('_', ' ');
}

export function PaperImportPanel({ onAccepted }: PaperImportPanelProps) {
  const [file, setFile] = useState<File | undefined>();
  const [job, setJob] = useState<PaperImportJob | undefined>();
  const importMutation = useSharedPaperPdfImport();

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
  }

  return (
    <form className="grid gap-3 rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <UploadRequirements title="Import paper PDF" extensions={['.pdf']} maxSizeLabel="25 MB" />
      <Input
        aria-label="PDF file"
        name="file"
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => setFile(event.target.files?.[0])}
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
      {job ? (
        <p role="status" className="text-sm font-medium text-success">
          {statusText(job)}
        </p>
      ) : null}
    </form>
  );
}
