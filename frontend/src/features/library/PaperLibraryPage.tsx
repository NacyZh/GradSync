import { useEffect, useMemo, useState } from 'react';

import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { PaperDetailPanel } from './PaperDetailPanel';
import { PaperFilters } from './PaperFilters';
import { PaperImportPanel } from './PaperImportPanel';
import { useSharedPaperDetail, useSharedPapers, type PaperRecord } from './api';

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
  const [query, setQuery] = useState('');
  const [author, setAuthor] = useState('');
  const [year, setYear] = useState('');
  const [keyword, setKeyword] = useState('');
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [acceptedImport, setAcceptedImport] = useState<PaperRecord | undefined>();
  const filters = useMemo(
    () => ({ query: query.trim(), author: author.trim(), year: year.trim(), keyword: keyword.trim() }),
    [author, keyword, query, year],
  );
  const papersQuery = useSharedPapers(filters);
  const papers = useMemo(() => papersQuery.data?.results ?? [], [papersQuery.data]);
  const detailQuery = useSharedPaperDetail(selectedId);
  const selectedSummary = papers.find((paper) => paper.id === selectedId);
  const selectedPaper =
    detailQuery.data ?? selectedSummary ?? (acceptedImport?.id === selectedId ? acceptedImport : undefined);
  const activeFilterText = [query, author, year, keyword].filter(Boolean).join(', ');

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
      <div className="grid gap-4 xl:grid-cols-[minmax(20rem,0.7fr)_minmax(28rem,1.3fr)]">
        <section className="panel" aria-label="Paper download">
          <div className="mb-4">
            <PaperImportPanel
              onAccepted={(paper) => {
                setAcceptedImport(paper);
                setSelectedId(paper.id);
              }}
            />
          </div>
          <PaperDetailPanel paper={selectedPaper} />
        </section>
        <section className="panel" aria-label="Shared paper search">
          <div className="mb-4 grid gap-3">
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
          <ul className="grid gap-2">
            {papers.map((paper) => (
              <li key={paper.id}>
                <button
                  type="button"
                  aria-label={`Select paper ${paperTitle(paper)}`}
                  aria-pressed={selectedId === paper.id}
                  className="w-full rounded-md border p-3 text-left hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => setSelectedId(paper.id)}
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
        </section>
      </div>
    </PageShell>
  );
}
