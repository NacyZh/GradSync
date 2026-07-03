import { Download } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

import { downloadTeacherFeedback, type TeacherFeedback, type WritingVersion } from './api';
import { StatusBadge } from '../../shared/ui/StatusBadge';

type WritingVersionHistoryProps = {
  versions: WritingVersion[];
  onSelectVersion: (version: WritingVersion) => void;
  selectedVersionId?: string;
};

export function WritingVersionHistory({ versions, onSelectVersion, selectedVersionId }: WritingVersionHistoryProps) {
  if (!versions.length) {
    return <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">No versions uploaded.</p>;
  }

  return (
    <ol className="grid gap-2" aria-label="Writing version history">
      {versions.map((version) => (
        <li key={version.id}>
          <button
            type="button"
            className="w-full rounded-md border p-3 text-left hover:bg-muted data-[selected=true]:border-primary"
            data-selected={version.id === selectedVersionId}
            onClick={() => onSelectVersion(version)}
          >
            <span className="mb-2 flex flex-wrap items-start justify-between gap-2">
              <strong>Version {version.versionNumber}</strong>
              <StatusBadge status={version.status} />
            </span>
            <span className="block text-sm text-muted-foreground">
              {version.draftFileName ?? 'Draft file'} · {(version.fileKind ?? 'writing').replaceAll('_', ' ')}
            </span>
            {version.feedback?.length ? (
              <span className="mt-2 block text-sm font-medium">Feedback available for version {version.versionNumber}</span>
            ) : null}
          </button>
        </li>
      ))}
    </ol>
  );
}

export function FeedbackDownloadList({ feedback }: { feedback: TeacherFeedback[] }) {
  const [downloadMessage, setDownloadMessage] = useState('');
  const [error, setError] = useState('');

  if (!feedback.length) {
    return <p className="text-sm text-muted-foreground">No teacher feedback yet.</p>;
  }

  async function onDownload(item: TeacherFeedback) {
    setError('');
    setDownloadMessage('');
    try {
      const descriptor = await downloadTeacherFeedback(item.id);
      setDownloadMessage(`Download ready: ${descriptor.filename}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    }
  }

  return (
    <div className="grid gap-2">
      {feedback.map((item) => (
        <article key={item.id} className="rounded-md border p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <StatusBadge status={item.status} />
            {item.notificationStatus ? <StatusBadge status={item.notificationStatus} /> : null}
          </div>
          {item.comments ? <p className="text-sm">{item.comments}</p> : null}
          <Button className="mt-3" type="button" variant="outline" onClick={() => onDownload(item)}>
            <Download className="h-4 w-4" aria-hidden="true" />
            Download annotated file
          </Button>
        </article>
      ))}
      {downloadMessage ? <p role="status" className="text-sm font-medium text-success">{downloadMessage}</p> : null}
      {error ? <p role="alert" className="text-sm font-medium text-destructive">{error}</p> : null}
    </div>
  );
}
