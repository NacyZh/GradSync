import { useEffect, useMemo, useState } from 'react';
import type { KeyboardEvent } from 'react';

import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { useAuth } from '../auth/AuthProvider';
import { useI18n } from '../i18n/I18nProvider';
import { PaperDetailPanel } from './PaperDetailPanel';
import { PaperFilters } from './PaperFilters';
import { PaperImportPanel } from './PaperImportPanel';
import { PaperPreviewPanel } from './PaperPreviewPanel';
import { useDeleteSharedPaper, useRenameSharedPaper, useSharedPaperDetail, useSharedPapers, type PaperRecord } from './api';

function paperTitle(paper: PaperRecord) {
  return paper.canonicalTitle || paper.title;
}

function getErrorMessage(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'message' in err) {
    return String(err.message);
  }
  return fallback;
}

function paperSourceLabel(paper: PaperRecord, fallback: string) {
  if (paper.sourceProject?.title) {
    return `Source: ${paper.sourceProject.title}`;
  }
  return paper.titleSource?.replaceAll('_', ' ') || fallback;
}

function paperMetadataSummary(paper: PaperRecord, unknownAuthors: string, unknownYear: string) {
  const authors = paper.authors.join(', ') || unknownAuthors;
  const year = paper.publicationYear ?? unknownYear;
  const venue = paper.venue ? ` · ${paper.venue}` : '';
  return `${authors} · ${year}${venue}`;
}

function withDefaultActionCapabilities(paper: PaperRecord | undefined, isMaintainer: boolean) {
  if (!paper || paper.actionCapabilities) {
    return paper;
  }
  const canUseFile = Boolean(paper.downloadAvailable || paper.uploadedFileId || paper.attachments?.length);
  const isActive = paper.status === 'active';
  return {
    ...paper,
    actionCapabilities: {
      canRename: isMaintainer && isActive,
      canDelete: isMaintainer && isActive,
      canDownload: isActive && canUseFile,
      canView: isActive,
    },
  };
}

export function PaperLibraryPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [author, setAuthor] = useState('');
  const [year, setYear] = useState('');
  const [keyword, setKeyword] = useState('');
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [acceptedImport, setAcceptedImport] = useState<PaperRecord | undefined>();
  const [duplicateSelection, setDuplicateSelection] = useState<PaperRecord | undefined>();
  const [renamedPaper, setRenamedPaper] = useState<PaperRecord | undefined>();
  const [deletedPaperIds, setDeletedPaperIds] = useState<Set<string>>(() => new Set());
  const filters = useMemo(
    () => ({ query: query.trim(), author: author.trim(), year: year.trim(), keyword: keyword.trim() }),
    [author, keyword, query, year],
  );
  const papersQuery = useSharedPapers(filters);
  const renameMutation = useRenameSharedPaper();
  const deleteMutation = useDeleteSharedPaper();
  const papers = useMemo(
    () =>
      (papersQuery.data?.results ?? [])
        .filter((paper) => !deletedPaperIds.has(paper.id))
        .map((paper) => (renamedPaper?.id === paper.id ? renamedPaper : paper)),
    [deletedPaperIds, papersQuery.data, renamedPaper],
  );
  const detailQuery = useSharedPaperDetail(selectedId);
  const selectedSummary = papers.find((paper) => paper.id === selectedId);
  const importedSelection =
    (acceptedImport?.id === selectedId ? acceptedImport : undefined) ??
    (duplicateSelection?.id === selectedId ? duplicateSelection : undefined);
  const selectedPaper =
    (renamedPaper?.id === selectedId ? renamedPaper : undefined) ??
    importedSelection ??
    detailQuery.data ??
    selectedSummary;
  const activeFilterText = [query, author, year, keyword].filter(Boolean).join(', ');
  const isMaintainer = user?.global_role === 'advisor' || user?.global_role === 'admin';
  const selectedPaperWithCapabilities = withDefaultActionCapabilities(selectedPaper, isMaintainer);

  function openPaper(paperId: string) {
    setSelectedId(paperId);
  }

  function handlePaperRowKeyDown(event: KeyboardEvent<HTMLButtonElement>, paperId: string) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openPaper(paperId);
    }
  }

  async function renameSelectedPaper(newTitle: string, reason = '') {
    if (!selectedId) {
      throw new Error(t('paperLibrarySelectBeforeRenaming'));
    }
    const renamed = await renameMutation.mutateAsync({
      paperId: selectedId,
      payload: { newTitle, reason },
    });
    setRenamedPaper(renamed);
    return renamed;
  }

  async function deleteSelectedPaper(reason = '') {
    if (!selectedId) {
      throw new Error(t('paperLibrarySelectBeforeDeleting'));
    }
    const paperId = selectedId;
    await deleteMutation.mutateAsync({
      paperId,
      payload: { reason },
    });
    setDeletedPaperIds((current) => {
      const next = new Set(current);
      next.add(paperId);
      return next;
    });
    setRenamedPaper((current) => (current?.id === paperId ? undefined : current));
    setAcceptedImport((current) => (current?.id === paperId ? undefined : current));
    setDuplicateSelection((current) => (current?.id === paperId ? undefined : current));
    setSelectedId(undefined);
  }

  useEffect(() => {
    if (!selectedId && papers.length > 0) {
      setSelectedId(papers[0].id);
    }
  }, [papers, selectedId]);

  return (
    <PageShell
      title={t('paperLibrary')}
      description={t('paperLibraryDescription')}
    >
      <div
        data-testid="paper-library-workspace"
        className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(16rem,0.65fr)_minmax(0,1.35fr)] xl:grid-cols-[minmax(16rem,0.65fr)_minmax(30rem,1.4fr)_minmax(18rem,0.85fr)]"
      >
        <section className="panel relative z-10 grid min-w-0 content-start gap-4" aria-label={t('paperLibraryImportDownloadRegion')}>
          <div>
            <PaperImportPanel
              onAccepted={(paper) => {
                setAcceptedImport(paper);
                setSelectedId(paper.id);
              }}
              onSelectPaper={(paper) => {
                setDuplicateSelection(paper);
                setSelectedId(paper.id);
              }}
              isMaintainer={isMaintainer}
            />
          </div>
          <PaperDetailPanel paper={selectedPaperWithCapabilities} variant="download" />
        </section>
        <section className="panel relative z-10 grid min-w-0 content-start gap-4" aria-label={t('paperLibrarySearchDisplayRegion')}>
          <div className="grid gap-3">
            <PaperFilters
              value={query}
              author={author}
              year={year}
              keyword={keyword}
              onChange={setQuery}
              onAuthorChange={setAuthor}
              onYearChange={setYear}
              onKeywordChange={setKeyword}
            />
          </div>
          {papersQuery.isLoading ? (
            <div data-testid="paper-layout-state" className="min-w-0">
              <DataState state="loading" title={t('paperLibraryLoadingTitle')} message={t('paperLibraryLoadingMessage')} />
            </div>
          ) : null}
          {papersQuery.error ? (
            <div data-testid="paper-layout-state" className="min-w-0">
              <DataState
                state="error"
                title={t('paperLibraryUnavailableTitle')}
                message={getErrorMessage(papersQuery.error, t('paperLibraryLoadError'))}
              />
            </div>
          ) : null}
          {!papersQuery.isLoading && !papersQuery.error && !papers.length ? (
            <div data-testid="paper-layout-state" className="min-w-0">
              <DataState
                state="empty"
                title={t('paperLibraryEmptyTitle')}
                message={
                  activeFilterText
                    ? `${t('paperLibraryEmptyFilteredPrefix')} ${activeFilterText}.`
                    : t('paperLibraryEmptyDefault')
                }
              />
            </div>
          ) : null}
          <div className="grid min-w-0 gap-4 overflow-hidden">
            <PaperDetailPanel paper={selectedPaperWithCapabilities} onRename={renameSelectedPaper} onDelete={deleteSelectedPaper} />
            <ul
              data-testid="paper-results-list"
              className="grid max-h-[32rem] min-w-0 content-start gap-2 overflow-y-auto overflow-x-hidden pr-1"
              aria-label={t('paperLibrarySearchResults')}
            >
              {papers.map((paper) => (
                <li key={paper.id} className="min-w-0">
                  <button
                    type="button"
                    aria-label={`${t('paperLibraryOpenPaperPrefix')} ${paperTitle(paper)}; ${t('paperLibrarySelectPaperPrefix')} ${paperTitle(paper)}`}
                    aria-pressed={selectedId === paper.id}
                    data-selected={selectedId === paper.id ? 'true' : 'false'}
                    data-testid="paper-result-row"
                    className={`grid min-h-16 w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 overflow-hidden rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                      selectedId === paper.id
                        ? 'border-primary bg-primary/10 shadow-sm'
                        : 'bg-background hover:bg-muted'
                    }`}
                    onClick={() => openPaper(paper.id)}
                    onKeyDown={(event) => handlePaperRowKeyDown(event, paper.id)}
                  >
                    <span className="grid min-w-0 gap-1">
                      <strong data-testid="paper-row-title" className="line-clamp-2 min-w-0 break-words text-sm leading-snug">
                        {paperTitle(paper)}
                      </strong>
                      <span data-testid="paper-row-metadata" className="block min-w-0 truncate text-xs text-muted-foreground">
                        {paperMetadataSummary(paper, t('paperLibraryUnknownAuthors'), t('paperLibraryUnknownYear'))}
                      </span>
                    </span>
                    <span className="max-w-[9rem] shrink-0 truncate rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground">
                      {paperSourceLabel(paper, t('paperLibrarySharedSource'))}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>
        <PaperPreviewPanel paper={selectedPaperWithCapabilities} />
      </div>
    </PageShell>
  );
}
