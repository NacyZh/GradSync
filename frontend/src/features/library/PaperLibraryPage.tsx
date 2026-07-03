import { useState } from 'react';
import { useParams } from 'react-router-dom';

import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { PaperDetailPanel } from './PaperDetailPanel';
import { PaperFilters } from './PaperFilters';
import { PaperImportPanel } from './PaperImportPanel';
import { usePapers, type PaperRecord } from './api';

export function PaperLibraryPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const [query, setQuery] = useState('');
  const [visibility, setVisibility] = useState('');
  const [selected, setSelected] = useState<PaperRecord | undefined>();
  const papersQuery = usePapers(projectId, query, visibility);
  const papers = papersQuery.data?.results ?? [];

  return (
    <PageShell title="Paper library" description="Upload, search, inspect, and download project-scoped papers.">
      <div className="grid gap-4 xl:grid-cols-[minmax(22rem,1fr)_minmax(20rem,0.8fr)]">
        <section className="panel" aria-label="Paper records">
          <div className="mb-4 grid gap-3">
            <PaperFilters value={query} visibility={visibility} onChange={setQuery} onVisibilityChange={setVisibility} />
            <PaperImportPanel projectId={projectId} />
          </div>
          {papersQuery.isLoading ? <DataState state="loading" title="Loading papers" message="Loading project papers." /> : null}
          {papersQuery.error ? <DataState state="error" title="Paper search failed" message={papersQuery.error.message} /> : null}
          {!papersQuery.isLoading && !papers.length ? <DataState state="empty" title="No papers" message="No papers match the current filters." /> : null}
          <ul className="grid gap-2">
            {papers.map((paper) => (
              <li key={paper.id}>
                <button type="button" className="w-full rounded-md border p-3 text-left hover:bg-muted" onClick={() => setSelected(paper)}>
                  <span className="flex flex-wrap items-start justify-between gap-2">
                    <strong>{paper.title}</strong>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground">{paper.visibility.replaceAll('_', ' ')}</span>
                  </span>
                  <span className="block text-sm text-muted-foreground">{paper.authors.join(', ')} · {paper.publicationYear ?? 'No year'}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel" aria-label="Paper detail">
          <PaperDetailPanel projectId={projectId} paper={selected ?? papers[0]} />
        </section>
      </div>
    </PageShell>
  );
}
