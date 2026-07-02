import { Download } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { downloadPaper, type PaperRecord } from './api';

export function PaperDetailPanel({ projectId, paper }: { projectId: number; paper?: PaperRecord }) {
  const [status, setStatus] = useState<{ filename: string; deliveryMode: 'direct_response' | 'signed_url' } | undefined>();
  const [error, setError] = useState<string | undefined>();
  if (!paper) return <p className="text-sm text-muted-foreground">Select a paper to inspect metadata and downloads.</p>;

  async function onDownload() {
    if (!paper) return;
    setError(undefined);
    try {
      setStatus(await downloadPaper(projectId, paper.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download unavailable');
    }
  }

  return (
    <article className="grid gap-3 rounded-md border p-4">
      <div>
        <h3 className="text-lg font-bold">{paper.title}</h3>
        <p className="text-sm text-muted-foreground">{paper.authors.join(', ')}</p>
      </div>
      <dl className="grid gap-2 text-sm">
        <div><dt className="font-semibold">Venue</dt><dd>{paper.venue || 'Unspecified'}</dd></div>
        <div><dt className="font-semibold">DOI</dt><dd>{paper.doi || 'Unspecified'}</dd></div>
        <div><dt className="font-semibold">Tags</dt><dd>{paper.tags?.join(', ') || 'No tags'}</dd></div>
      </dl>
      <Button type="button" onClick={onDownload} disabled={!paper.attachments?.length}>
        <Download className="h-4 w-4" aria-hidden="true" />
        Download
      </Button>
      <DownloadStatus descriptor={status} error={error} />
    </article>
  );
}
