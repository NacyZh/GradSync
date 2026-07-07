import { Download, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';

import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import { downloadPaper, downloadSharedPaper, type PaperRecord } from './api';

type PaperDetailPanelProps = {
  projectId?: number;
  paper?: PaperRecord;
  variant?: 'detail' | 'download';
  onRename?: (newTitle: string, reason?: string) => Promise<PaperRecord>;
  onDelete?: (reason?: string) => Promise<void>;
};

function getErrorMessage(err: unknown) {
  if (err && typeof err === 'object' && 'message' in err) {
    return String(err.message);
  }
  return 'Download unavailable';
}

export function PaperDetailPanel({ projectId, paper, variant = 'detail', onRename, onDelete }: PaperDetailPanelProps) {
  const [status, setStatus] = useState<{ filename: string; deliveryMode: 'direct_response' | 'signed_url' } | undefined>();
  const [error, setError] = useState<string | undefined>();
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameTitle, setRenameTitle] = useState('');
  const [renameError, setRenameError] = useState<string | undefined>();
  const [isSavingRename, setIsSavingRename] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleteError, setDeleteError] = useState<string | undefined>();
  const [isDeleting, setIsDeleting] = useState(false);
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
  const viewerAvailable = paper.viewerAvailable !== false && paper.status === 'active';
  const canRename = Boolean(variant === 'detail' && onRename && paper.actionCapabilities?.canRename);
  const canDelete = Boolean(variant === 'detail' && onDelete && paper.actionCapabilities?.canDelete);

  async function onDownload() {
    if (!paper) return;
    setError(undefined);
    try {
      setStatus(projectId ? await downloadPaper(projectId, paper.id) : await downloadSharedPaper(paper.id));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  function startRename() {
    setRenameTitle(displayTitle);
    setRenameError(undefined);
    setIsConfirmingDelete(false);
    setIsRenaming(true);
  }

  async function submitRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanedTitle = renameTitle.trim();
    if (!cleanedTitle) {
      setRenameError('Paper title is required.');
      return;
    }
    setRenameError(undefined);
    setIsSavingRename(true);
    try {
      await onRename?.(cleanedTitle, '');
      setIsRenaming(false);
    } catch (err) {
      setRenameError(getErrorMessage(err));
    } finally {
      setIsSavingRename(false);
    }
  }

  function startDelete() {
    setDeleteReason('');
    setDeleteError(undefined);
    setIsRenaming(false);
    setIsConfirmingDelete(true);
  }

  async function submitDelete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDeleteError(undefined);
    setIsDeleting(true);
    try {
      await onDelete?.(deleteReason.trim());
      setIsConfirmingDelete(false);
    } catch (err) {
      setDeleteError(getErrorMessage(err));
    } finally {
      setIsDeleting(false);
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
          <div className="flex flex-wrap items-center gap-2">
            <VisibilityBadge visibility={paper.visibility} />
            {canRename ? (
              <Button type="button" variant="outline" size="sm" onClick={startRename} aria-label="Rename paper">
                <Pencil className="h-4 w-4" aria-hidden="true" />
                Rename
              </Button>
            ) : null}
            {canDelete ? (
              <Button type="button" variant="outline" size="sm" onClick={startDelete} aria-label="Delete paper">
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Delete
              </Button>
            ) : null}
          </div>
        </div>
        <p className="text-sm text-muted-foreground">{authors.join(', ') || 'Unknown authors'}</p>
      </div>
      {isRenaming ? (
        <form onSubmit={submitRename} className="grid gap-2 rounded-md border p-3">
          <label className="grid gap-1 text-sm font-semibold">
            New paper title
            <input
              aria-label="New paper title"
              className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm font-normal"
              value={renameTitle}
              maxLength={500}
              onChange={(event) => setRenameTitle(event.target.value)}
            />
          </label>
          {renameError ? (
            <p role="alert" className="text-sm text-destructive">
              {renameError}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isSavingRename}>
              Save title
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsRenaming(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : null}
      {isConfirmingDelete ? (
        <form onSubmit={submitDelete} className="grid gap-2 rounded-md border border-destructive/40 p-3">
          <div className="grid gap-1 text-sm">
            <p className="font-semibold text-destructive">Delete {displayTitle}</p>
            <p className="text-muted-foreground">
              The paper will leave ordinary browse, open, and download workflows.
            </p>
          </div>
          <label className="grid gap-1 text-sm font-semibold">
            Delete reason
            <input
              aria-label="Delete reason"
              className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm font-normal"
              value={deleteReason}
              maxLength={255}
              onChange={(event) => setDeleteReason(event.target.value)}
            />
          </label>
          {deleteError ? (
            <p role="alert" className="text-sm text-destructive">
              {deleteError}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isDeleting}>
              Confirm delete
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsConfirmingDelete(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : null}
      <div
        role={viewerAvailable ? undefined : 'alert'}
        className={`rounded-md border p-3 text-sm ${
          viewerAvailable ? 'bg-muted/30 text-muted-foreground' : 'border-destructive text-destructive'
        }`}
      >
        <p className="font-semibold text-foreground">In-page viewer</p>
        <p>
          {viewerAvailable
            ? 'PDF preview opens here when the stored file is available.'
            : 'This paper is unavailable and cannot be opened.'}
        </p>
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
