import { Download, Pencil, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';

import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import { useI18n } from '../i18n/I18nProvider';
import { downloadPaper, downloadSharedPaper, previewSharedPaperFile, type PaperRecord } from './api';

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
  const [previewUrl, setPreviewUrl] = useState<string | undefined>();
  const [previewError, setPreviewError] = useState<string | undefined>();
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const canPreview = Boolean(
    paper &&
      paper.status === 'active' &&
      paper.viewerAvailable !== false &&
      (paper.downloadAvailable || paper.uploadedFileId || paper.attachments?.length),
  );

  useEffect(() => {
    let cancelled = false;
    setPreviewError(undefined);
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return undefined;
    });
    if (!paper || projectId || variant !== 'detail' || !canPreview) {
      setIsPreviewLoading(false);
      return () => undefined;
    }
    setIsPreviewLoading(true);
    previewSharedPaperFile(paper.id)
      .then((objectUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setPreviewUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) {
          setPreviewError(getErrorMessage(err, t('paperLibraryPreviewUnavailable')));
        }
      })
      .finally(() => {
        if (!cancelled) setIsPreviewLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [canPreview, paper, projectId, t, variant]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  if (!paper) {
    if (variant === 'download') {
      return (
        <section aria-label={t('paperLibrarySelectedPaperDownload')} className="grid gap-3 rounded-md border p-4">
          <div>
            <h3 className="text-base font-bold">{t('paperLibrarySelectedPaper')}</h3>
            <p className="text-sm text-muted-foreground">{t('paperLibrarySelectBeforeDownload')}</p>
          </div>
          <Button type="button" disabled aria-label={t('paperLibraryDownloadSelectedPaper')}>
            <Download className="h-4 w-4" aria-hidden="true" />
            {t('download')}
          </Button>
        </section>
      );
    }
    return (
      <section aria-label={t('paperLibrarySelectedPaperDetails')} className="grid gap-2 rounded-md border border-dashed p-4">
        <h3 className="text-base font-bold">{t('paperLibrarySelectedPaperDetails')}</h3>
        <p className="text-sm text-muted-foreground">{t('paperLibraryMetadataAfterSelection')}</p>
      </section>
    );
  }
  const displayTitle = paper.canonicalTitle || paper.title;
  const authors = Array.isArray(paper.authors) ? paper.authors : [];
  const keywords = paper.keywords ?? paper.tags ?? [];
  const canDownload = Boolean(paper.downloadAvailable || paper.uploadedFileId || paper.attachments?.length);
  const viewerAvailable = canPreview;
  const canRename = Boolean(variant === 'detail' && onRename && paper.actionCapabilities?.canRename);
  const canDelete = Boolean(variant === 'detail' && onDelete && paper.actionCapabilities?.canDelete);

  async function onDownload() {
    if (!paper) return;
    setError(undefined);
    try {
      setStatus(
        projectId
          ? await downloadPaper(projectId, paper.id)
          : await downloadSharedPaper(paper.id, paper.defaultDownloadFilename ?? `${displayTitle}.pdf`),
      );
    } catch (err) {
      setError(getErrorMessage(err, t('paperLibraryDownloadFallbackError')));
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
      setRenameError(t('paperLibraryTitleRequired'));
      return;
    }
    setRenameError(undefined);
    setIsSavingRename(true);
    try {
      await onRename?.(cleanedTitle, '');
      setIsRenaming(false);
    } catch (err) {
      setRenameError(getErrorMessage(err, t('paperLibraryActionUnavailable')));
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
      setDeleteError(getErrorMessage(err, t('paperLibraryActionUnavailable')));
    } finally {
      setIsDeleting(false);
    }
  }

  if (variant === 'download') {
    return (
      <section aria-label={t('paperLibrarySelectedPaperDownload')} className="grid gap-3 rounded-md border p-4">
        <div>
          <h3 className="text-base font-bold">{t('paperLibrarySelectedPaper')}</h3>
          <p className="mt-1 font-semibold">{displayTitle}</p>
          <p className="text-sm text-muted-foreground">{authors.join(', ') || t('paperLibraryUnknownAuthors')}</p>
        </div>
        <Button
          type="button"
          onClick={onDownload}
          disabled={!canDownload}
          aria-label={`${t('download')} ${displayTitle}`}
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          {t('download')}
        </Button>
        {!canDownload ? (
          <p className="text-sm text-muted-foreground">{t('paperLibraryDownloadUnavailable')}</p>
        ) : null}
        <DownloadStatus descriptor={status} error={error} startedLabel={t('paperLibraryDownloadStarted')} />
      </section>
    );
  }

  return (
    <section aria-label={t('paperLibrarySelectedPaperDetails')} className="grid gap-3 rounded-md border p-4">
      <div>
        <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
          <h3 className="text-lg font-bold">{displayTitle}</h3>
          <div className="flex flex-wrap items-center gap-2">
            <VisibilityBadge visibility={paper.visibility} />
            {canRename ? (
              <Button type="button" variant="outline" size="sm" onClick={startRename} aria-label={t('paperLibraryRename')}>
                <Pencil className="h-4 w-4" aria-hidden="true" />
                {t('paperLibraryRenameButton')}
              </Button>
            ) : null}
            {canDelete ? (
              <Button type="button" variant="outline" size="sm" onClick={startDelete} aria-label={t('paperLibraryDelete')}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {t('paperLibraryDeleteButton')}
              </Button>
            ) : null}
          </div>
        </div>
        <p className="text-sm text-muted-foreground">{authors.join(', ') || t('paperLibraryUnknownAuthors')}</p>
      </div>
      {isRenaming ? (
        <form onSubmit={submitRename} className="grid gap-2 rounded-md border p-3">
          <label className="grid gap-1 text-sm font-semibold">
            {t('paperLibraryNewTitle')}
            <input
              aria-label={t('paperLibraryNewTitle')}
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
              {t('paperLibrarySaveTitle')}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsRenaming(false)}>
              {t('paperLibraryCancel')}
            </Button>
          </div>
        </form>
      ) : null}
      {isConfirmingDelete ? (
        <form onSubmit={submitDelete} className="grid gap-2 rounded-md border border-destructive/40 p-3">
          <div className="grid gap-1 text-sm">
            <p className="font-semibold text-destructive">{t('paperLibraryDeleteButton')} {displayTitle}</p>
            <p className="text-muted-foreground">{t('paperLibraryDeleteDescription')}</p>
          </div>
          <label className="grid gap-1 text-sm font-semibold">
            {t('paperLibraryDeleteReason')}
            <input
              aria-label={t('paperLibraryDeleteReason')}
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
              {t('paperLibraryConfirmDelete')}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsConfirmingDelete(false)}>
              {t('paperLibraryCancel')}
            </Button>
          </div>
        </form>
      ) : null}
      <div
        role={viewerAvailable ? undefined : 'alert'}
        className={`grid gap-3 rounded-md border p-3 text-sm ${
          viewerAvailable ? 'bg-muted/30 text-muted-foreground' : 'border-destructive text-destructive'
        }`}
      >
        <p className="font-semibold text-foreground">{t('paperLibraryInPageViewer')}</p>
        <p>
          {isPreviewLoading
            ? t('paperLibraryPreviewLoading')
            : previewError ||
              (viewerAvailable
                ? t('paperLibraryViewerAvailable')
                : t('paperLibraryViewerUnavailable'))}
        </p>
        {previewUrl ? (
          <iframe
            title={`${displayTitle} ${t('paperLibraryPdfPreview')}`}
            src={previewUrl}
            className="h-[34rem] w-full rounded-md border bg-background"
          />
        ) : viewerAvailable ? (
          <div className="grid min-h-80 place-items-center rounded-md border border-dashed bg-background text-center text-sm text-muted-foreground">
            {isPreviewLoading ? t('paperLibraryPreviewLoading') : t('paperLibraryPreviewUnavailable')}
          </div>
        ) : null}
      </div>
      <dl className="grid gap-2 text-sm">
        {paper.title !== displayTitle ? <div><dt className="font-semibold">{t('paperLibraryOriginalTitle')}</dt><dd>{paper.title}</dd></div> : null}
        <div><dt className="font-semibold">{t('paperLibraryVenue')}</dt><dd>{paper.venue || t('paperLibraryUnspecified')}</dd></div>
        <div><dt className="font-semibold">{t('paperLibraryDoi')}</dt><dd>{paper.doi || t('paperLibraryUnspecified')}</dd></div>
        <div><dt className="font-semibold">{t('paperLibraryKeywords')}</dt><dd>{keywords.join(', ') || t('paperLibraryNoKeywords')}</dd></div>
        <div><dt className="font-semibold">{t('paperLibraryTitleSource')}</dt><dd>{paper.titleSource?.replaceAll('_', ' ') || t('paperLibraryUnspecified')}</dd></div>
        <div><dt className="font-semibold">{t('paperLibraryChecksum')}</dt><dd className="break-all">{paper.checksumSha256 || t('paperLibraryUnavailableValue')}</dd></div>
      </dl>
    </section>
  );
}
