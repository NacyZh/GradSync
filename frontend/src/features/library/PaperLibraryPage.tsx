import { useEffect, useMemo, useState } from 'react';
import type { KeyboardEvent } from 'react';

import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { useAuth } from '../auth/AuthProvider';
import { PaperDetailPanel } from './PaperDetailPanel';
import { PaperFilters } from './PaperFilters';
import { PaperImportPanel } from './PaperImportPanel';
import { useDeleteSharedPaper, useRenameSharedPaper, useSharedPaperDetail, useSharedPapers, type PaperRecord } from './api';

function paperTitle(paper: PaperRecord) {
  return paper.canonicalTitle || paper.title;
}

function getErrorMessage(err: unknown) {
  if (err && typeof err === 'object' && 'message' in err) {
    return String(err.message);
  }
  return 'Unable to load the shared paper library.';
}

export function PaperLibraryPage() {
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
  const selectedPaper =
    (renamedPaper?.id === selectedId ? renamedPaper : undefined) ??
    detailQuery.data ??
    selectedSummary ??
    (acceptedImport?.id === selectedId ? acceptedImport : undefined) ??
    (duplicateSelection?.id === selectedId ? duplicateSelection : undefined);
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
      throw new Error('Select a paper before renaming.');
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
      throw new Error('Select a paper before deleting.');
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
      title="Paper library"
      description="Search, inspect, and download shared papers available to active GradSync users."
    >
      <div
        data-testid="paper-library-workspace"
        className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(20rem,0.72fr)_minmax(30rem,1.28fr)]"
      >
        <section className="panel grid min-w-0 content-start gap-4" aria-label="Paper import and download">
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
        <section className="panel grid min-w-0 content-start gap-4" aria-label="Shared paper search and display">
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
            <DataState state="loading" title="Loading papers" message="Loading shared papers." />
          ) : null}
          {papersQuery.error ? (
            <DataState
              state="error"
              title="Paper library unavailable"
              message={getErrorMessage(papersQuery.error)}
            />
          ) : null}
          {!papersQuery.isLoading && !papersQuery.error && !papers.length ? (
            <DataState
              state="empty"
              title="No shared papers"
              message={
                activeFilterText
                  ? `No shared papers match ${activeFilterText}.`
                  : 'No shared papers are available yet.'
              }
            />
          ) : null}
          <div className="grid gap-4 lg:grid-cols-[minmax(16rem,0.95fr)_minmax(18rem,1.05fr)]">
            <ul
              data-testid="paper-results-list"
              className="grid content-start gap-2 overflow-y-auto pr-1"
              style={{ maxHeight: '34rem' }}
              aria-label="Shared paper results"
            >
              {papers.map((paper) => (
                <li key={paper.id}>
                  <button
                    type="button"
                    aria-label={`Open paper ${paperTitle(paper)}; Select paper ${paperTitle(paper)}`}
                    aria-pressed={selectedId === paper.id}
                    data-selected={selectedId === paper.id ? 'true' : 'false'}
                    className={`min-h-24 w-full rounded-md border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      selectedId === paper.id
                        ? 'border-primary bg-primary/10 shadow-sm'
                        : 'hover:bg-muted'
                    }`}
                    onClick={() => openPaper(paper.id)}
                    onKeyDown={(event) => handlePaperRowKeyDown(event, paper.id)}
                  >
                    <span className="flex flex-wrap items-start justify-between gap-2">
                      <strong>{paperTitle(paper)}</strong>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground">
                        {paper.titleSource?.replaceAll('_', ' ') || 'shared'}
                      </span>
                    </span>
                    <span className="block text-sm text-muted-foreground">
                      {paper.authors.join(', ')} · {paper.publicationYear ?? 'No year'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <PaperDetailPanel paper={selectedPaper} onRename={renameSelectedPaper} onDelete={deleteSelectedPaper} />
          </div>
        </section>
      </div>
    </PageShell>
  );
}
