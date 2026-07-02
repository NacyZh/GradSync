import { Download } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { downloadCodeVersion, type CodeArtifact } from './api';

export function CodeArtifactActions({ projectId, artifact }: { projectId: number; artifact: CodeArtifact }) {
  const [descriptor, setDescriptor] = useState<{ filename: string; deliveryMode: 'direct_response' | 'signed_url' } | undefined>();
  const version = artifact.latestVersion;

  async function onDownload() {
    if (!version) return;
    setDescriptor(await downloadCodeVersion(projectId, artifact.id, version.id));
  }

  return (
    <div className="grid gap-2">
      <Button type="button" onClick={onDownload} disabled={!version}>
        <Download className="h-4 w-4" aria-hidden="true" />
        Download
      </Button>
      <DownloadStatus descriptor={descriptor} />
    </div>
  );
}
