import { useEffect, useMemo, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { useParams } from 'react-router-dom';

import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import { CodeArtifactActions } from './CodeArtifactActions';
import { CodeArtifactFilters } from './CodeArtifactFilters';
import { CodeArtifactImportForm } from './CodeArtifactImportForm';
import { CodeArtifactVersionPanel } from './CodeArtifactVersionPanel';
import { useCodeArtifacts, useDeleteCodeArtifact, useRenameCodeArtifact, useSharedCodeArtifacts, type CodeArtifact } from './api';

export function CodeRepositoryPage() {
  const projectIdParam = useParams().projectId;
  const projectId = Number(projectIdParam ?? 0);
  const standalone = !projectIdParam;
  const [query, setQuery] = useState('');
  const [visibility, setVisibility] = useState('');
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [uploadedArtifacts, setUploadedArtifacts] = useState<Record<string, CodeArtifact>>({});
  const [renamedArtifacts, setRenamedArtifacts] = useState<Record<string, CodeArtifact>>({});
  const [deletedArtifactIds, setDeletedArtifactIds] = useState<Set<string>>(() => new Set());
  const projectArtifactsQuery = useCodeArtifacts(projectId, query, visibility);
  const sharedArtifactsQuery = useSharedCodeArtifacts(query, standalone);
  const artifactsQuery = standalone ? sharedArtifactsQuery : projectArtifactsQuery;
  const renameMutation = useRenameCodeArtifact(projectId);
  const deleteMutation = useDeleteCodeArtifact(projectId);
  const artifacts = useMemo(() => {
    const byId = new Map<string, CodeArtifact>();
    for (const artifact of artifactsQuery.data?.results ?? []) {
      byId.set(artifact.id, artifact);
    }
    for (const artifact of Object.values(uploadedArtifacts)) {
      byId.set(artifact.id, artifact);
    }
    for (const artifact of Object.values(renamedArtifacts)) {
      byId.set(artifact.id, artifact);
    }
    return Array.from(byId.values()).filter((artifact) => !deletedArtifactIds.has(artifact.id));
  }, [artifactsQuery.data, deletedArtifactIds, renamedArtifacts, uploadedArtifacts]);
  const selectedArtifact = artifacts.find((artifact) => artifact.id === selectedId) ?? artifacts[0];
  const selectedArtifactForDisplay = standalone && selectedArtifact
    ? {
        ...selectedArtifact,
        actionCapabilities: {
          canView: selectedArtifact.actionCapabilities?.canView ?? selectedArtifact.status === 'active',
          canDownload: selectedArtifact.actionCapabilities?.canDownload ?? Boolean(selectedArtifact.archiveFileId || selectedArtifact.latestVersion),
          canRename: false,
          canDelete: false,
        },
      }
    : selectedArtifact;

  function selectArtifact(artifact: CodeArtifact) {
    setSelectedId(artifact.id);
  }

  function handleArtifactRowKeyDown(event: KeyboardEvent<HTMLButtonElement>, artifact: CodeArtifact) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectArtifact(artifact);
    }
  }

  async function renameSelectedArtifact(newName: string, reason?: string) {
    if (!selectedArtifact) {
      throw new Error('Select a code artifact before renaming');
    }
    const renamed = await renameMutation.mutateAsync({
      artifactId: selectedArtifact.id,
      payload: { name: newName, reason },
    });
    setRenamedArtifacts((current) => ({ ...current, [renamed.id]: renamed }));
    return renamed;
  }

  async function deleteSelectedArtifact() {
    if (!selectedArtifact) {
      throw new Error('Select a code artifact before deleting');
    }
    const deletedId = selectedArtifact.id;
    await deleteMutation.mutateAsync(deletedId);
    setDeletedArtifactIds((current) => {
      const next = new Set(current);
      next.add(deletedId);
      return next;
    });
    setRenamedArtifacts((current) => {
      const next = { ...current };
      delete next[deletedId];
      return next;
    });
    setUploadedArtifacts((current) => {
      const next = { ...current };
      delete next[deletedId];
      return next;
    });
    setSelectedId(undefined);
  }

  function handleUploadedArtifact(artifact: CodeArtifact) {
    setUploadedArtifacts((current) => ({ ...current, [artifact.id]: artifact }));
    setSelectedId(artifact.id);
  }

  useEffect(() => {
    if (!artifacts.length) {
      setSelectedId(undefined);
      return;
    }
    if (!selectedId || !artifacts.some((artifact) => artifact.id === selectedId)) {
      setSelectedId(artifacts[0].id);
    }
  }, [artifacts, selectedId]);

  return (
    <PageShell
      title={standalone ? 'Shared code' : 'Code repository'}
      description={
        standalone
          ? 'Upload, search, inspect, and download group shared code archives.'
          : 'Upload, search, inspect, and download compressed code archives.'
      }
    >
      <div
        data-testid="code-repository-workspace"
        className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(16rem,0.68fr)_minmax(0,1.32fr)]"
      >
        <section className="panel relative z-10 grid min-w-0 content-start gap-4" aria-label="Code repository upload and download region">
          <CodeArtifactImportForm projectId={projectId} onUploaded={handleUploadedArtifact} standalone={standalone} />
          <div data-testid="code-selected-download-region" className="grid min-w-0 gap-3">
            <CodeArtifactVersionPanel artifact={selectedArtifactForDisplay} variant="download" />
            {selectedArtifactForDisplay ? <CodeArtifactActions projectId={projectId} artifact={selectedArtifactForDisplay} /> : null}
          </div>
        </section>
        <section className="panel relative z-10 grid min-w-0 content-start gap-4" aria-label="Code repository search and display region">
          <div className="grid min-w-0 gap-3">
              <CodeArtifactFilters
                value={query}
                visibility={visibility}
                onChange={setQuery}
                onVisibilityChange={setVisibility}
                showVisibility={!standalone}
              />
          </div>
          {artifactsQuery.isLoading ? (
            <div data-testid="code-layout-state" className="min-w-0">
              <DataState state="loading" title="Loading code" message="Loading project code artifacts." />
            </div>
          ) : null}
          {artifactsQuery.error ? (
            <div data-testid="code-layout-state" className="min-w-0">
              <DataState state="error" title="Code search failed" message={artifactsQuery.error.message} />
            </div>
          ) : null}
          {!artifactsQuery.isLoading && !artifactsQuery.error && !artifacts.length ? (
            <div data-testid="code-layout-state" className="min-w-0">
              <DataState state="empty" title="No code artifacts" message="No code artifacts match the current filters." />
            </div>
          ) : null}
          <div className="grid min-w-0 gap-4 overflow-hidden">
            <div data-testid="code-selected-detail-region" className="min-w-0">
              <CodeArtifactVersionPanel artifact={selectedArtifactForDisplay} />
              {selectedArtifactForDisplay ? (
                <div className="mt-3 min-w-0">
                  <CodeArtifactActions
                    projectId={projectId}
                    artifact={selectedArtifactForDisplay}
                    onRename={renameSelectedArtifact}
                    onDelete={deleteSelectedArtifact}
                    showDownload={false}
                  />
                </div>
              ) : null}
            </div>
            <ul
              data-testid="code-results-list"
              className="grid max-h-[32rem] min-w-0 content-start gap-2 overflow-y-auto overflow-x-hidden pr-1"
              aria-label="Code artifact search results"
            >
              {artifacts.map((artifact) => (
                <li key={artifact.id} className="min-w-0">
                  <button
                    type="button"
                    aria-label={`Select code artifact ${artifact.name}`}
                    aria-pressed={selectedArtifact?.id === artifact.id}
                    data-selected={selectedArtifact?.id === artifact.id ? 'true' : 'false'}
                    data-testid="code-result-row"
                    className={`grid min-h-16 w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 overflow-hidden rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                      selectedArtifact?.id === artifact.id
                        ? 'border-primary bg-primary/10 shadow-sm'
                        : 'bg-background hover:bg-muted'
                    }`}
                    onClick={() => selectArtifact(artifact)}
                    onKeyDown={(event) => handleArtifactRowKeyDown(event, artifact)}
                  >
                    <span className="grid min-w-0 gap-1">
                      <strong className="line-clamp-2 min-w-0 break-words text-sm leading-snug">{artifact.name}</strong>
                      <span className="block min-w-0 truncate text-xs text-muted-foreground">
                        {artifact.description || artifact.latestVersion?.filename || 'No description'}
                      </span>
                    </span>
                    <span className="max-w-[9rem] shrink-0">
                      <VisibilityBadge visibility={artifact.visibility} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </PageShell>
  );
}
