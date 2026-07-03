import { Download } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { downloadCodeArtifact, type CodeArtifact } from './api';

export function CodeArtifactActions({ projectId, artifact }: { projectId: number; artifact: CodeArtifact }) {
  const [descriptor, setDescriptor] = useState<{ filename: string; deliveryMode: 'direct_response' | 'signed_url' } | undefined>();
  const [error, setError] = useState<string | undefined>();
  const canDownload = Boolean(artifact.archiveFileId || artifact.latestVersion);

  async function onDownload() {
    setError(undefined);
    try {
      setDescriptor(await downloadCodeArtifact(projectId, artifact));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download unavailable');
    }
  }

  return (
    <div className="grid gap-2">
      <Button type="button" onClick={onDownload} disabled={!canDownload}>
        <Download className="h-4 w-4" aria-hidden="true" />
        Download
      </Button>
      <DownloadStatus descriptor={descriptor} error={error} />
    </div>
  );
}
