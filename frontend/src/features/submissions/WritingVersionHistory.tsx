import { Download } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { getErrorMessage } from '../../shared/api/errors';
import {
  downloadTeacherFeedback,
  downloadWritingVersion,
  type TeacherFeedback,
  type WritingVersion,
} from './api';
import { StatusBadge } from '../../shared/ui/StatusBadge';

type WritingVersionHistoryProps = {
  versions: WritingVersion[];
  onSelectVersion: (version: WritingVersion) => void;
  selectedVersionId?: string;
};

export function WritingVersionHistory({ versions, onSelectVersion, selectedVersionId }: WritingVersionHistoryProps) {
  const { notify } = useAppFeedback();

  if (!versions.length) {
    return <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">No versions uploaded.</p>;
  }

  async function onDownloadVersion(version: WritingVersion) {
    try {
      const descriptor = await downloadWritingVersion(version.id, version.draftFileName ?? 'writing-version');
      notify(`Download started: ${descriptor.filename}`, 'success');
    } catch (err) {
      notify(getErrorMessage(err), 'error');
    }
  }

  return (
    <div className="grid gap-2">
      <ol className="grid gap-2" aria-label="Writing version history">
        {versions.map((version) => (
          <li key={version.id} className="rounded-md border p-3 data-[selected=true]:border-primary" data-selected={version.id === selectedVersionId}>
            <button
              type="button"
              className="w-full text-left hover:text-primary"
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
            <Button className="mt-3" type="button" variant="outline" onClick={() => onDownloadVersion(version)}>
              <Download className="h-4 w-4" aria-hidden="true" />
              Download draft file
            </Button>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function FeedbackDownloadList({ feedback }: { feedback: TeacherFeedback[] }) {
  const { notify } = useAppFeedback();

  if (!feedback.length) {
    return <p className="text-sm text-muted-foreground">No teacher feedback yet.</p>;
  }

  async function onDownload(item: TeacherFeedback) {
    try {
      const descriptor = await downloadTeacherFeedback(item.id, item.annotatedFileName ?? 'teacher-feedback');
      notify(`Download started: ${descriptor.filename}`, 'success');
    } catch (err) {
      notify(getErrorMessage(err), 'error');
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
    </div>
  );
}
