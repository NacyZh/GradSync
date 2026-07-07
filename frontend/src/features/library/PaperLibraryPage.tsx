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
    selectedSummary ??
    importedSelection ??
    detailQuery.data;
  const activeFilterText = [query, author, year, keyword].filter(Boolean).join(', ');
  const isMaintainer = user?.global_role === 'advisor' || user?.global_role === 'admin';

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
        className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(15rem,0.65fr)_minmax(21rem,0.95fr)_minmax(20rem,1fr)]"
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
          <PaperDetailPanel paper={selectedPaper} variant="download" />
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
            <DataState state="loading" title={t('paperLibraryLoadingTitle')} message={t('paperLibraryLoadingMessage')} />
          ) : null}
          {papersQuery.error ? (
            <DataState
              state="error"
              title={t('paperLibraryUnavailableTitle')}
              message={getErrorMessage(papersQuery.error, t('paperLibraryLoadError'))}
            />
          ) : null}
          {!papersQuery.isLoading && !papersQuery.error && !papers.length ? (
            <DataState
              state="empty"
              title={t('paperLibraryEmptyTitle')}
              message={
                activeFilterText
                  ? `${t('paperLibraryEmptyFilteredPrefix')} ${activeFilterText}.`
                  : t('paperLibraryEmptyDefault')
              }
            />
          ) : null}
          <div className="grid min-w-0 gap-4">
            <ul
              data-testid="paper-results-list"
              className="grid content-start gap-2 overflow-y-auto pr-1"
              style={{ maxHeight: '28rem' }}
              aria-label={t('paperLibrarySearchResults')}
            >
              {papers.map((paper) => (
                <li key={paper.id}>
                  <button
                    type="button"
                    aria-label={`${t('paperLibraryOpenPaperPrefix')} ${paperTitle(paper)}; ${t('paperLibrarySelectPaperPrefix')} ${paperTitle(paper)}`}
                    aria-pressed={selectedId === paper.id}
                    data-selected={selectedId === paper.id ? 'true' : 'false'}
                    className={`min-h-24 w-full min-w-0 overflow-hidden rounded-md border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      selectedId === paper.id
                        ? 'border-primary bg-primary/10 shadow-sm'
                        : 'hover:bg-muted'
                    }`}
                    onClick={() => openPaper(paper.id)}
                    onKeyDown={(event) => handlePaperRowKeyDown(event, paper.id)}
                  >
                    <span className="flex min-w-0 flex-wrap items-start justify-between gap-2">
                      <strong className="min-w-0 break-words">{paperTitle(paper)}</strong>
                      <span className="max-w-full shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground">
                        {paper.titleSource?.replaceAll('_', ' ') || t('paperLibrarySharedSource')}
                      </span>
                    </span>
                    <span className="block min-w-0 break-words text-sm text-muted-foreground">
                      {paper.authors.join(', ') || t('paperLibraryUnknownAuthors')} · {paper.publicationYear ?? t('paperLibraryUnknownYear')}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <PaperDetailPanel paper={selectedPaper} onRename={renameSelectedPaper} onDelete={deleteSelectedPaper} />
          </div>
        </section>
        <PaperPreviewPanel paper={selectedPaper} />
      </div>
    </PageShell>
  );
}
