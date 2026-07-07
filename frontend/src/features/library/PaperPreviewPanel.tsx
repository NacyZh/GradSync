import { FileText } from 'lucide-react';
import { useEffect, useState } from 'react';

import { useI18n } from '../i18n/I18nProvider';
import { previewSharedPaperFile, type PaperRecord } from './api';

type PaperPreviewPanelProps = {
  paper?: PaperRecord;
};

function getErrorMessage(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'message' in err) {
    return String(err.message);
  }
  return fallback;
}

export function PaperPreviewPanel({ paper }: PaperPreviewPanelProps) {
  const { t } = useI18n();
  const [previewUrl, setPreviewUrl] = useState<string | undefined>();
  const [previewError, setPreviewError] = useState<string | undefined>();
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const paperId = paper?.id;
  const displayTitle = paper ? paper.canonicalTitle || paper.title : '';
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
    if (!paperId || !canPreview) {
      setIsPreviewLoading(false);
      return () => undefined;
    }
    setIsPreviewLoading(true);
    previewSharedPaperFile(paperId)
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
  }, [canPreview, paperId, t]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  if (!paper) {
    return (
      <section data-testid="paper-preview-panel" aria-label={t('paperLibraryPreviewRegion')} className="panel relative z-0 grid min-w-0 content-start gap-3 overflow-hidden lg:col-span-2 xl:col-span-1">
        <div className="flex min-w-0 items-center gap-2">
          <FileText className="h-4 w-4 shrink-0" aria-hidden="true" />
          <h3 className="min-w-0 text-base font-bold">{t('paperLibraryInPageViewer')}</h3>
        </div>
        <p data-testid="paper-preview-state" className="min-w-0 break-words text-sm text-muted-foreground">{t('paperLibraryMetadataAfterSelection')}</p>
        <div className="grid min-h-80 place-items-center rounded-md border border-dashed bg-background p-4 text-center text-sm text-muted-foreground">
          {t('paperLibraryPreviewUnavailable')}
        </div>
      </section>
    );
  }

  return (
    <section data-testid="paper-preview-panel" aria-label={t('paperLibraryPreviewRegion')} className="panel relative z-0 grid min-w-0 content-start gap-3 overflow-hidden lg:col-span-2 xl:col-span-1">
      <div className="flex min-w-0 items-center gap-2">
        <FileText className="h-4 w-4 shrink-0" aria-hidden="true" />
        <h3 className="min-w-0 break-words text-base font-bold">{t('paperLibraryInPageViewer')}</h3>
      </div>
      <p
        data-testid="paper-preview-state"
        role={canPreview ? undefined : 'alert'}
        className={`min-w-0 break-words text-sm ${canPreview ? 'text-muted-foreground' : 'text-destructive'}`}
      >
        {isPreviewLoading
          ? t('paperLibraryPreviewLoading')
          : previewError ||
            (canPreview
              ? t('paperLibraryViewerAvailable')
              : t('paperLibraryViewerUnavailable'))}
      </p>
      {previewUrl ? (
        <iframe
          title={`${displayTitle} ${t('paperLibraryPdfPreview')}`}
          src={previewUrl}
          className="h-[60vh] min-h-[22rem] w-full min-w-0 max-w-full rounded-md border bg-background md:min-h-[30rem] xl:h-[72vh] xl:min-h-[34rem]"
        />
      ) : canPreview ? (
        <div className="grid min-h-80 min-w-0 place-items-center rounded-md border border-dashed bg-background p-4 text-center text-sm text-muted-foreground">
          {isPreviewLoading ? t('paperLibraryPreviewLoading') : t('paperLibraryPreviewUnavailable')}
        </div>
      ) : null}
    </section>
  );
}
