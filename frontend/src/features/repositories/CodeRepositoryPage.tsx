import { useState } from 'react';
import { useParams } from 'react-router-dom';

import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import { CodeArtifactActions } from './CodeArtifactActions';
import { CodeArtifactFilters } from './CodeArtifactFilters';
import { CodeArtifactImportForm } from './CodeArtifactImportForm';
import { CodeArtifactVersionPanel } from './CodeArtifactVersionPanel';
import { useCodeArtifacts, type CodeArtifact } from './api';

export function CodeRepositoryPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const [query, setQuery] = useState('');
  const [visibility, setVisibility] = useState('');
  const [selected, setSelected] = useState<CodeArtifact | undefined>();
  const artifactsQuery = useCodeArtifacts(projectId, query, visibility);
  const artifacts = artifactsQuery.data?.results ?? [];

  return (
    <PageShell title="Code repository" description="Upload, search, inspect, and download compressed code archives.">
      <div className="grid gap-4 xl:grid-cols-[minmax(22rem,1fr)_minmax(20rem,0.8fr)]">
        <section className="panel" aria-label="Code artifacts">
          <div className="mb-4 grid gap-3">
            <CodeArtifactFilters value={query} visibility={visibility} onChange={setQuery} onVisibilityChange={setVisibility} />
            <CodeArtifactImportForm projectId={projectId} />
          </div>
          {artifactsQuery.isLoading ? <DataState state="loading" title="Loading code" message="Loading project code artifacts." /> : null}
          {artifactsQuery.error ? <DataState state="error" title="Code search failed" message={artifactsQuery.error.message} /> : null}
          {!artifactsQuery.isLoading && !artifacts.length ? <DataState state="empty" title="No code artifacts" message="No code artifacts match the current filters." /> : null}
          <ul className="grid gap-2">
            {artifacts.map((artifact) => (
              <li key={artifact.id}>
                <button
                  type="button"
                  aria-label={`Select code artifact ${artifact.name}`}
                  className="w-full rounded-md border p-3 text-left hover:bg-muted"
                  onClick={() => setSelected(artifact)}
                >
                  <span className="mb-2 flex flex-wrap items-start justify-between gap-2">
                    <strong>{artifact.name}</strong>
                    <VisibilityBadge visibility={artifact.visibility} />
                  </span>
                  <span className="block text-sm text-muted-foreground">{artifact.description || artifact.latestVersion?.filename || 'No description'}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel" aria-label="Code artifact detail">
          <CodeArtifactVersionPanel artifact={selected ?? artifacts[0]} />
          {(selected ?? artifacts[0]) ? <CodeArtifactActions projectId={projectId} artifact={(selected ?? artifacts[0]) as CodeArtifact} /> : null}
        </section>
      </div>
    </PageShell>
  );
}
