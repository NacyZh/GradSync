import { useState } from 'react';
import { useParams } from 'react-router-dom';

import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { CodeArtifactActions } from './CodeArtifactActions';
import { CodeArtifactFilters } from './CodeArtifactFilters';
import { CodeArtifactUploadForm } from './CodeArtifactUploadForm';
import { CodeArtifactVersionPanel } from './CodeArtifactVersionPanel';
import { useCodeArtifacts, type CodeArtifact } from './api';

export function CodeRepositoryPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<CodeArtifact | undefined>();
  const artifactsQuery = useCodeArtifacts(projectId, query);
  const artifacts = artifactsQuery.data?.results ?? [];

  return (
    <PageShell title="Code repository" description="Upload, search, version, and download project-scoped code artifacts.">
      <div className="grid gap-4 xl:grid-cols-[minmax(22rem,1fr)_minmax(20rem,0.8fr)]">
        <section className="panel" aria-label="Code artifacts">
          <div className="mb-4 grid gap-3">
            <CodeArtifactFilters value={query} onChange={setQuery} />
            <CodeArtifactUploadForm projectId={projectId} />
          </div>
          {artifactsQuery.isLoading ? <DataState state="loading" title="Loading code" message="Loading project code artifacts." /> : null}
          {artifactsQuery.error ? <DataState state="error" title="Code search failed" message={artifactsQuery.error.message} /> : null}
          {!artifactsQuery.isLoading && !artifacts.length ? <DataState state="empty" title="No code artifacts" message="No code artifacts match the current filters." /> : null}
          <ul className="grid gap-2">
            {artifacts.map((artifact) => (
              <li key={artifact.id}>
                <button type="button" className="w-full rounded-md border p-3 text-left hover:bg-muted" onClick={() => setSelected(artifact)}>
                  <strong>{artifact.name}</strong>
                  <span className="block text-sm text-muted-foreground">{artifact.latestVersion?.versionLabel ?? 'No version'} · {artifact.status}</span>
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
