import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, FileUp, FolderOpen, X } from 'lucide-react';
import { useRef, useState, type FormEvent } from 'react';
import { useParams } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';

import { DataState } from '../../shared/ui/DataState';
import { LocalizedValidation } from '../../shared/ui/LocalizedValidation';
import { PageShell } from '../../shared/ui/PageShell';
import { SourceProjectBadge, VisibilityStateBadge } from '../../shared/ui/BoundaryBadges';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import {
  createProjectMaterial,
  downloadProjectMaterial,
  listProjectMaterials,
  updateProjectMaterialVisibility,
  type ProjectMaterial,
} from './api';
import { useProjectLiveRefresh } from './useProjectLiveRefresh';

export function ProjectMaterialsPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const queryClient = useQueryClient();
  const { notify } = useAppFeedback();
  const liveRefresh = useProjectLiveRefresh(projectId);
  const [title, setTitle] = useState('');
  const [materialType, setMaterialType] = useState<ProjectMaterial['materialType']>('document');
  const [visibility, setVisibility] = useState<ProjectMaterial['visibility']>('project-only');
  const [file, setFile] = useState<File | undefined>();
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  function clearFile() {
    setFile(undefined);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }
  const materialsQuery = useQuery({
    queryKey: ['projectMaterials', projectId],
    queryFn: () => listProjectMaterials(projectId),
    enabled: Boolean(projectId),
  });
  const createMutation = useMutation({
    mutationFn: (payload: { materialType: ProjectMaterial['materialType']; file: File; title?: string; visibility: ProjectMaterial['visibility'] }) =>
      createProjectMaterial(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectMaterials', projectId] });
      setTitle('');
      clearFile();
    },
  });
  const visibilityMutation = useMutation({
    mutationFn: ({ materialId, nextVisibility }: { materialId: string; nextVisibility: ProjectMaterial['visibility'] }) =>
      updateProjectMaterialVisibility(projectId, materialId, { visibility: nextVisibility }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projectMaterials', projectId] }),
  });
  const downloadMutation = useMutation({
    mutationFn: (materialId: string) => downloadProjectMaterial(projectId, materialId),
    onSuccess: (descriptor) => notify(`Download ready: ${descriptor.filename}`, 'success'),
    onError: (downloadError) => notify(downloadError.message, 'error'),
  });

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setError('');
    try {
      await createMutation.mutateAsync({ materialType, file, title, visibility });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Project material upload failed');
    }
  }

  return (
    <PageShell title="Project materials" description="Project-owned papers, code, and documents with controlled project-only or group-wide visibility.">
      <div className="grid gap-4 xl:grid-cols-[minmax(20rem,0.8fr)_minmax(24rem,1.2fr)]">
        <section className="panel" aria-label="Create project material">
          <h2>Create material</h2>
          <form className="mt-4 grid gap-3" onSubmit={onSubmit}>
            <Input aria-label="Material title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Material title" />
            <select
              aria-label="Material type"
              className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={materialType}
              onChange={(event) => setMaterialType(event.target.value as ProjectMaterial['materialType'])}
            >
              <option value="document">Document</option>
              <option value="code">Code</option>
              <option value="paper">Paper</option>
            </select>
            <select
              aria-label="Material visibility"
              className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={visibility}
              onChange={(event) => setVisibility(event.target.value as ProjectMaterial['visibility'])}
            >
              <option value="project-only">Project-only</option>
              <option value="group-wide">Group-wide</option>
            </select>
            <input ref={fileInputRef} className="hidden" aria-label="Material file" type="file" onChange={(event) => setFile(event.target.files?.[0])} required />
            <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
              <Button type="button" variant="outline" className="min-w-0" onClick={() => fileInputRef.current?.click()} aria-label={file ? 'Reselect material' : 'Choose material'}>
                <FolderOpen className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="truncate">{file ? 'Reselect file' : 'Choose file'}</span>
              </Button>
              {file ? (
                <Button type="button" variant="ghost" className="min-w-0" onClick={clearFile} aria-label="Clear material file">
                  <X className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span className="truncate">Clear</span>
                </Button>
              ) : null}
            </div>
            {file ? <p className="min-w-0 truncate text-sm text-muted-foreground">Selected file: {file.name}</p> : null}
            <Button type="submit" disabled={!file || createMutation.isPending}>
              <FileUp className="h-4 w-4" aria-hidden="true" />
              Upload material
            </Button>
            <LocalizedValidation message={error} />
          </form>
        </section>

        <section className="panel" aria-label="Project material list">
          <h2>Materials</h2>
          {liveRefresh.state === 'stale' ? (
            <DataState state="warning" title="Materials may be stale" message="Last successful material list is still visible while live refresh retries." />
          ) : null}
          {materialsQuery.isLoading ? <DataState state="loading" title="Loading materials" message="Loading project materials." /> : null}
          {materialsQuery.error ? <DataState state="error" title="Materials unavailable" message={materialsQuery.error.message} /> : null}
          {!materialsQuery.isLoading && !materialsQuery.data?.results.length ? (
            <DataState state="empty" title="No project materials" message="Upload a project-owned material to manage its visibility." />
          ) : null}
          <ul className="mt-4 grid gap-3">
            {(materialsQuery.data?.results ?? []).map((material) => (
              <li key={material.id} className="rounded-md border p-3">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <strong>{material.displayName || `${material.materialType} ${material.backingRecordId}`}</strong>
                  <span className="flex flex-wrap gap-2">
                    <VisibilityStateBadge visibility={material.visibility} />
                    <SourceProjectBadge title={material.sourceProject.title} />
                  </span>
                </div>
                <p className="text-sm capitalize text-muted-foreground">
                  {material.materialType} · {material.classificationState.replaceAll('_', ' ')}
                </p>
                {material.actionCapabilities.canDownload || material.actionCapabilities.canChangeVisibility ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      aria-label={`Download ${material.displayName || `${material.materialType} ${material.backingRecordId}`}`}
                      disabled={!material.actionCapabilities.canDownload || downloadMutation.isPending}
                      onClick={() => downloadMutation.mutate(material.id)}
                    >
                      <Download className="h-4 w-4" aria-hidden="true" />
                      Download
                    </Button>
                    {material.actionCapabilities.canChangeVisibility ? (
                      <>
                        <Button
                          type="button"
                          variant="outline"
                          disabled={material.visibility === 'project-only' || visibilityMutation.isPending}
                          onClick={() => visibilityMutation.mutate({ materialId: material.id, nextVisibility: 'project-only' })}
                        >
                          Set project-only
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          disabled={material.visibility === 'group-wide' || visibilityMutation.isPending}
                          onClick={() => visibilityMutation.mutate({ materialId: material.id, nextVisibility: 'group-wide' })}
                        >
                          Set group-wide
                        </Button>
                      </>
                    ) : null}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </PageShell>
  );
}
