import { Download } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import { downloadPaper, downloadSharedPaper, type PaperRecord } from './api';

type PaperDetailPanelProps = {
  projectId?: number;
  paper?: PaperRecord;
  variant?: 'detail' | 'download';
};

function getErrorMessage(err: unknown) {
  if (err && typeof err === 'object' && 'message' in err) {
    return String(err.message);
  }
  return 'Download unavailable';
}

export function PaperDetailPanel({ projectId, paper, variant = 'detail' }: PaperDetailPanelProps) {
  const [status, setStatus] = useState<{ filename: string; deliveryMode: 'direct_response' | 'signed_url' } | undefined>();
  const [error, setError] = useState<string | undefined>();
  if (!paper) {
    if (variant === 'download') {
      return (
        <section aria-label="Selected paper download" className="grid gap-3 rounded-md border p-4">
          <div>
            <h3 className="text-base font-bold">Selected paper</h3>
            <p className="text-sm text-muted-foreground">Select a paper from the results before downloading.</p>
          </div>
          <Button type="button" disabled aria-label="Download selected paper">
            <Download className="h-4 w-4" aria-hidden="true" />
            Download
          </Button>
        </section>
      );
    }
    return (
      <section aria-label="Selected paper details" className="grid gap-2 rounded-md border border-dashed p-4">
        <h3 className="text-base font-bold">Selected paper details</h3>
        <p className="text-sm text-muted-foreground">Paper metadata appears after a result is selected.</p>
      </section>
    );
  }
  const displayTitle = paper.canonicalTitle || paper.title;
  const authors = Array.isArray(paper.authors) ? paper.authors : [];
  const keywords = paper.keywords ?? paper.tags ?? [];
  const canDownload = Boolean(paper.downloadAvailable || paper.uploadedFileId || paper.attachments?.length);

  async function onDownload() {
    if (!paper) return;
    setError(undefined);
    try {
      setStatus(projectId ? await downloadPaper(projectId, paper.id) : await downloadSharedPaper(paper.id));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  if (variant === 'download') {
    return (
      <section aria-label="Selected paper download" className="grid gap-3 rounded-md border p-4">
        <div>
          <h3 className="text-base font-bold">Selected paper</h3>
          <p className="mt-1 font-semibold">{displayTitle}</p>
          <p className="text-sm text-muted-foreground">{authors.join(', ') || 'Unknown authors'}</p>
        </div>
        <Button
          type="button"
          onClick={onDownload}
          disabled={!canDownload}
          aria-label={`Download ${displayTitle}`}
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          Download
        </Button>
        {!canDownload ? (
          <p className="text-sm text-muted-foreground">Download is unavailable for the selected paper.</p>
        ) : null}
        <DownloadStatus descriptor={status} error={error} />
      </section>
    );
  }

  return (
    <section aria-label="Selected paper details" className="grid gap-3 rounded-md border p-4">
      <div>
        <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
          <h3 className="text-lg font-bold">{displayTitle}</h3>
          <VisibilityBadge visibility={paper.visibility} />
        </div>
        <p className="text-sm text-muted-foreground">{authors.join(', ') || 'Unknown authors'}</p>
      </div>
      <dl className="grid gap-2 text-sm">
        {paper.title !== displayTitle ? <div><dt className="font-semibold">Original title</dt><dd>{paper.title}</dd></div> : null}
        <div><dt className="font-semibold">Venue</dt><dd>{paper.venue || 'Unspecified'}</dd></div>
        <div><dt className="font-semibold">DOI</dt><dd>{paper.doi || 'Unspecified'}</dd></div>
        <div><dt className="font-semibold">Keywords</dt><dd>{keywords.join(', ') || 'No keywords'}</dd></div>
        <div><dt className="font-semibold">Title source</dt><dd>{paper.titleSource?.replaceAll('_', ' ') || 'Unspecified'}</dd></div>
        <div><dt className="font-semibold">Checksum</dt><dd className="break-all">{paper.checksumSha256 || 'Unavailable'}</dd></div>
      </dl>
    </section>
  );
}
