import { Download, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/shared/ui/primitives/button';

import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { downloadCodeArtifact, type CodeArtifact } from './api';

type CodeArtifactActionsProps = {
  projectId: number;
  artifact: CodeArtifact;
  onRename?: (newName: string, reason?: string) => Promise<CodeArtifact>;
  onDelete?: () => Promise<void>;
  showDownload?: boolean;
};

function getErrorMessage(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'message' in err) {
    return String(err.message);
  }
  return fallback;
}

export function CodeArtifactActions({ projectId, artifact, onRename, onDelete, showDownload = true }: CodeArtifactActionsProps) {
  const [descriptor, setDescriptor] = useState<{ filename: string; deliveryMode: 'direct_response' | 'signed_url' } | undefined>();
  const [error, setError] = useState<string | undefined>();
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameName, setRenameName] = useState('');
  const [renameError, setRenameError] = useState<string | undefined>();
  const [isSavingRename, setIsSavingRename] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | undefined>();
  const [isDeleting, setIsDeleting] = useState(false);
  const hasDownload = Boolean(artifact.archiveFileId || artifact.latestVersion);
  const canDownload = artifact.actionCapabilities?.canDownload ?? hasDownload;
  const canRename = Boolean(onRename && artifact.actionCapabilities?.canRename);
  const canDelete = Boolean(onDelete && artifact.actionCapabilities?.canDelete);

  async function onDownload() {
    setError(undefined);
    try {
      setDescriptor(await downloadCodeArtifact(projectId, artifact));
    } catch (err) {
      setError(getErrorMessage(err, 'Download unavailable'));
    }
  }

  function startRename() {
    setRenameName(artifact.name);
    setRenameError(undefined);
    setIsConfirmingDelete(false);
    setIsRenaming(true);
  }

  async function submitRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanedName = renameName.trim();
    if (!cleanedName) {
      setRenameError('Code artifact name is required');
      return;
    }
    setRenameError(undefined);
    setIsSavingRename(true);
    try {
      await onRename?.(cleanedName, '');
      setIsRenaming(false);
    } catch (err) {
      setRenameError(getErrorMessage(err, 'Rename unavailable'));
    } finally {
      setIsSavingRename(false);
    }
  }

  function startDelete() {
    setDeleteError(undefined);
    setIsRenaming(false);
    setIsConfirmingDelete(true);
  }

  async function submitDelete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDeleteError(undefined);
    setIsDeleting(true);
    try {
      await onDelete?.();
      setIsConfirmingDelete(false);
    } catch (err) {
      setDeleteError(getErrorMessage(err, 'Delete unavailable'));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="grid min-w-0 gap-2">
      <div className="flex min-w-0 flex-wrap gap-2">
        {showDownload ? (
          <Button type="button" onClick={onDownload} disabled={!canDownload || !hasDownload} className="min-w-0" aria-label="Download">
            <Download className="h-4 w-4" aria-hidden="true" />
            <span className="truncate">Download</span>
          </Button>
        ) : null}
        {canRename ? (
          <Button type="button" variant="outline" size="sm" onClick={startRename} aria-label="Rename code artifact" className="min-w-0">
            <Pencil className="h-4 w-4" aria-hidden="true" />
            <span className="truncate">Rename</span>
          </Button>
        ) : null}
        {canDelete ? (
          <Button type="button" variant="outline" size="sm" onClick={startDelete} aria-label="Delete code artifact" className="min-w-0">
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            <span className="truncate">Delete</span>
          </Button>
        ) : null}
      </div>
      {isRenaming ? (
        <form onSubmit={submitRename} className="grid min-w-0 gap-2 rounded-md border p-3">
          <label className="grid min-w-0 gap-1 text-sm font-semibold">
            New code artifact name
            <input
              aria-label="New code artifact name"
              className="min-h-10 min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm font-normal"
              value={renameName}
              maxLength={255}
              onChange={(event) => setRenameName(event.target.value)}
            />
          </label>
          {renameError ? (
            <p role="alert" className="min-w-0 break-words text-sm text-destructive">
              {renameError}
            </p>
          ) : null}
          <div className="flex min-w-0 flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isSavingRename}>
              Save name
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsRenaming(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : null}
      {isConfirmingDelete ? (
        <form onSubmit={submitDelete} className="grid min-w-0 gap-2 rounded-md border border-destructive/40 p-3">
          <div className="grid min-w-0 gap-1 text-sm">
            <p className="min-w-0 break-words font-semibold text-destructive">Delete {artifact.name}</p>
            <p className="text-muted-foreground">This archives the selected code artifact and removes it from ordinary search and download.</p>
          </div>
          {deleteError ? (
            <p role="alert" className="min-w-0 break-words text-sm text-destructive">
              {deleteError}
            </p>
          ) : null}
          <div className="flex min-w-0 flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isDeleting}>
              Confirm delete
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsConfirmingDelete(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : null}
      <DownloadStatus descriptor={descriptor} error={error} />
    </div>
  );
}
