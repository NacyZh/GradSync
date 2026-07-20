import { Download, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/shared/ui/primitives/button';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import { useI18n } from '../i18n/I18nProvider';
import { downloadPaper, downloadSharedPaper, type PaperRecord } from './api';

type PaperDetailPanelProps = {
  projectId?: number;
  paper?: PaperRecord;
  variant?: 'detail' | 'download';
  onRename?: (newTitle: string, reason?: string) => Promise<PaperRecord>;
  onDelete?: (reason?: string) => Promise<void>;
};

function getErrorMessage(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'message' in err) {
    return String(err.message);
  }
  return fallback;
}

export function PaperDetailPanel({ projectId, paper, variant = 'detail', onRename, onDelete }: PaperDetailPanelProps) {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameTitle, setRenameTitle] = useState('');
  const [isSavingRename, setIsSavingRename] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [deleteReason, setDeleteReason] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  if (!paper) {
    if (variant === 'download') {
      return (
        <section data-testid="paper-detail-panel" aria-label={t('paperLibrarySelectedPaperDownload')} className="grid min-w-0 gap-3 overflow-hidden rounded-md border p-4">
          <div>
            <h3 className="text-base font-bold">{t('paperLibrarySelectedPaper')}</h3>
            <p className="text-sm text-muted-foreground">{t('paperLibrarySelectBeforeDownload')}</p>
          </div>
          <div data-testid="paper-primary-action-group" className="flex min-w-0 flex-wrap gap-2">
            <Button type="button" disabled aria-label={t('paperLibraryDownloadSelectedPaper')} className="min-w-0">
              <Download className="h-4 w-4" aria-hidden="true" />
              {t('download')}
            </Button>
          </div>
        </section>
      );
    }
    return (
      <section data-testid="paper-detail-panel" aria-label={t('paperLibrarySelectedPaperDetails')} className="grid min-w-0 gap-2 overflow-hidden rounded-md border border-dashed p-4">
        <h3 className="text-base font-bold">{t('paperLibrarySelectedPaperDetails')}</h3>
        <p className="text-sm text-muted-foreground">{t('paperLibraryMetadataAfterSelection')}</p>
      </section>
    );
  }
  const displayTitle = paper.canonicalTitle || paper.title;
  const authors = Array.isArray(paper.authors) ? paper.authors : [];
  const keywords = paper.keywords ?? paper.tags ?? [];
  const canDownload = Boolean(paper.downloadAvailable || paper.uploadedFileId || paper.attachments?.length);
  const canRename = Boolean(variant === 'detail' && onRename && paper.actionCapabilities?.canRename);
  const canDelete = Boolean(variant === 'detail' && onDelete && paper.actionCapabilities?.canDelete);

  async function onDownload() {
    if (!paper) return;
    try {
      const descriptor =
        projectId
          ? await downloadPaper(projectId, paper.id)
          : await downloadSharedPaper(paper.id, paper.defaultDownloadFilename ?? `${displayTitle}.pdf`);
      notify(`${t('paperLibraryDownloadStarted')} ${descriptor.filename}`, 'success');
    } catch (err) {
      notify(getErrorMessage(err, t('paperLibraryDownloadFallbackError')), 'error');
    }
  }

  function startRename() {
    setRenameTitle(displayTitle);
    setIsConfirmingDelete(false);
    setIsRenaming(true);
  }

  async function submitRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanedTitle = renameTitle.trim();
    if (!cleanedTitle) {
      notify(t('paperLibraryTitleRequired'), 'error');
      return;
    }
    setIsSavingRename(true);
    try {
      await onRename?.(cleanedTitle, '');
      setIsRenaming(false);
      notify(t('paperLibraryRename'), 'success');
    } catch (err) {
      notify(getErrorMessage(err, t('paperLibraryActionUnavailable')), 'error');
    } finally {
      setIsSavingRename(false);
    }
  }

  function startDelete() {
    setDeleteReason('');
    setIsRenaming(false);
    setIsConfirmingDelete(true);
  }

  async function submitDelete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsDeleting(true);
    try {
      await onDelete?.(deleteReason.trim());
      setIsConfirmingDelete(false);
      notify(t('paperLibraryDelete'), 'success');
    } catch (err) {
      notify(getErrorMessage(err, t('paperLibraryActionUnavailable')), 'error');
    } finally {
      setIsDeleting(false);
    }
  }

  if (variant === 'download') {
    return (
      <section data-testid="paper-detail-panel" aria-label={t('paperLibrarySelectedPaperDownload')} className="grid min-w-0 gap-3 overflow-hidden rounded-md border p-4">
        <div className="min-w-0">
          <h3 className="text-base font-bold">{t('paperLibrarySelectedPaper')}</h3>
          <p data-testid="paper-detail-title" className="mt-1 min-w-0 break-words font-semibold">{displayTitle}</p>
          <p className="min-w-0 truncate text-sm text-muted-foreground">{authors.join(', ') || t('paperLibraryUnknownAuthors')}</p>
        </div>
        <div data-testid="paper-primary-action-group" className="flex min-w-0 flex-wrap gap-2">
          <Button
            type="button"
            onClick={onDownload}
            disabled={!canDownload}
            aria-label={`${t('download')} ${displayTitle}`}
            className="min-w-0"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            <span className="truncate">{t('download')}</span>
          </Button>
        </div>
        {!canDownload ? (
          <p className="text-sm text-muted-foreground">{t('paperLibraryDownloadUnavailable')}</p>
        ) : null}
      </section>
    );
  }

  return (
    <section data-testid="paper-detail-panel" aria-label={t('paperLibrarySelectedPaperDetails')} className="grid min-w-0 gap-3 overflow-hidden rounded-md border p-4">
      <div className="min-w-0">
        <div className="mb-2 grid min-w-0 gap-2 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
          <h3 data-testid="paper-detail-title" className="min-w-0 break-words text-lg font-bold leading-snug">{displayTitle}</h3>
          <div data-testid="paper-primary-action-group" className="flex min-w-0 flex-wrap items-center gap-2 md:justify-end">
            <VisibilityBadge visibility={paper.visibility} />
            {canRename ? (
              <Button type="button" variant="outline" size="sm" onClick={startRename} aria-label={t('paperLibraryRename')} className="min-w-0">
                <Pencil className="h-4 w-4" aria-hidden="true" />
                <span className="truncate">{t('paperLibraryRenameButton')}</span>
              </Button>
            ) : null}
            {canDelete ? (
              <Button type="button" variant="outline" size="sm" onClick={startDelete} aria-label={t('paperLibraryDelete')} className="min-w-0">
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                <span className="truncate">{t('paperLibraryDeleteButton')}</span>
              </Button>
            ) : null}
          </div>
        </div>
        <p className="min-w-0 break-words text-sm text-muted-foreground">{authors.join(', ') || t('paperLibraryUnknownAuthors')}</p>
      </div>
      {isRenaming ? (
        <form onSubmit={submitRename} className="grid min-w-0 gap-2 rounded-md border p-3">
          <label className="grid gap-1 text-sm font-semibold">
            {t('paperLibraryNewTitle')}
            <input
              aria-label={t('paperLibraryNewTitle')}
              className="min-h-10 min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm font-normal"
              value={renameTitle}
              maxLength={500}
              onChange={(event) => setRenameTitle(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isSavingRename}>
              {t('paperLibrarySaveTitle')}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsRenaming(false)}>
              {t('paperLibraryCancel')}
            </Button>
          </div>
        </form>
      ) : null}
      {isConfirmingDelete ? (
        <form onSubmit={submitDelete} className="grid min-w-0 gap-2 rounded-md border border-destructive/40 p-3">
          <div className="grid min-w-0 gap-1 text-sm">
            <p className="min-w-0 break-words font-semibold text-destructive">{t('paperLibraryDeleteButton')} {displayTitle}</p>
            <p className="text-muted-foreground">{t('paperLibraryDeleteDescription')}</p>
          </div>
          <label className="grid gap-1 text-sm font-semibold">
            {t('paperLibraryDeleteReason')}
            <input
              aria-label={t('paperLibraryDeleteReason')}
              className="min-h-10 min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm font-normal"
              value={deleteReason}
              maxLength={255}
              onChange={(event) => setDeleteReason(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isDeleting}>
              {t('paperLibraryConfirmDelete')}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsConfirmingDelete(false)}>
              {t('paperLibraryCancel')}
            </Button>
          </div>
        </form>
      ) : null}
      <dl className="grid min-w-0 gap-2 text-sm">
        {paper.title !== displayTitle ? <div className="min-w-0"><dt className="font-semibold">{t('paperLibraryOriginalTitle')}</dt><dd className="min-w-0 break-words">{paper.title}</dd></div> : null}
        <div className="min-w-0"><dt className="font-semibold">{t('paperLibraryVenue')}</dt><dd className="min-w-0 break-words">{paper.venue || t('paperLibraryUnspecified')}</dd></div>
        <div className="min-w-0"><dt className="font-semibold">{t('paperLibraryDoi')}</dt><dd className="min-w-0 break-words">{paper.doi || t('paperLibraryUnspecified')}</dd></div>
        <div className="min-w-0"><dt className="font-semibold">{t('paperLibraryKeywords')}</dt><dd className="min-w-0 break-words">{keywords.join(', ') || t('paperLibraryNoKeywords')}</dd></div>
        <div className="min-w-0"><dt className="font-semibold">{t('paperLibraryTitleSource')}</dt><dd className="min-w-0 break-words">{paper.titleSource?.replaceAll('_', ' ') || t('paperLibraryUnspecified')}</dd></div>
        <div className="min-w-0"><dt className="font-semibold">{t('paperLibraryChecksum')}</dt><dd className="break-all">{paper.checksumSha256 || t('paperLibraryUnavailableValue')}</dd></div>
      </dl>
    </section>
  );
}
