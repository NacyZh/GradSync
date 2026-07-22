import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Code2, Download, FileText, FileUp, FolderOpen, Newspaper, Search, X } from 'lucide-react';
import { useRef, useState, type FormEvent } from 'react';
import { useParams } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { translateUiText } from '@/shared/i18n/translate';

import { getErrorMessage } from '../../shared/api/errors';
import { DataState } from '../../shared/ui/DataState';
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
  const { locale } = useI18n();
  const { notify } = useAppFeedback();
  const liveRefresh = useProjectLiveRefresh(projectId);
  const [title, setTitle] = useState('');
  const [materialType, setMaterialType] = useState<ProjectMaterial['materialType']>('document');
  const [materialFilter, setMaterialFilter] = useState<ProjectMaterial['materialType']>('document');
  const [materialSearch, setMaterialSearch] = useState('');
  const [visibility, setVisibility] = useState<ProjectMaterial['visibility']>('project-only');
  const [file, setFile] = useState<File | undefined>();
  const fileInputRef = useRef<HTMLInputElement>(null);

  function clearFile() {
    setFile(undefined);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }
  const materialsQuery = useQuery({
    queryKey: ['projectMaterials', projectId, materialFilter, materialSearch],
    queryFn: () => listProjectMaterials(projectId, { type: materialFilter, search: materialSearch }),
    enabled: Boolean(projectId),
  });
  const createMutation = useMutation({
    mutationFn: (payload: { materialType: ProjectMaterial['materialType']; file: File; title?: string; visibility: ProjectMaterial['visibility'] }) =>
      createProjectMaterial(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectMaterials', projectId] });
      setTitle('');
      clearFile();
      notify('Material uploaded', 'success');
    },
    onError: (uploadError) => notify(getErrorMessage(uploadError), 'error'),
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
    createMutation.mutate({ materialType, file, title, visibility });
  }

  const materialCategories: Array<{ value: ProjectMaterial['materialType']; label: string; icon: typeof FileText }> = [
    { value: 'document', label: 'Document', icon: FileText },
    { value: 'code', label: 'Code', icon: Code2 },
    { value: 'paper', label: 'Paper', icon: Newspaper },
  ];
  const filteredMaterials = materialsQuery.data?.results ?? [];
  const ui = (value: string) => translateUiText(value, locale);

  return (
    <PageShell title="Project materials" description="Project-owned papers, code, and documents with controlled project-only or group-wide visibility.">
      <div className="grid gap-4 xl:grid-cols-[minmax(20rem,0.8fr)_minmax(24rem,1.2fr)]">
        <section className="panel" aria-label="Create project material">
          <h2>Create material</h2>
          <form className="mt-4 grid gap-3" noValidate onSubmit={onSubmit}>
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
          </form>
        </section>

        <section className="panel grid h-[min(36rem,calc(100vh-10rem))] min-h-[30rem] grid-rows-[auto_auto_auto_1fr] overflow-hidden" aria-label="Project material list">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2>Materials</h2>
              <p className="text-sm text-muted-foreground">{ui(`${materialsQuery.data?.count ?? 0} ${materialFilter} materials`)}</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3">
            <div className="grid grid-cols-3 gap-2" role="tablist" aria-label="Material category">
              {materialCategories.map((category) => {
                const Icon = category.icon;
                const active = materialFilter === category.value;
                return (
                  <Button
                    key={category.value}
                    type="button"
                    variant={active ? 'default' : 'outline'}
                    className="min-w-0 px-2"
                    role="tab"
                    aria-selected={active}
                    aria-label={ui(`Show ${category.label} materials`)}
                    onClick={() => setMaterialFilter(category.value)}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="truncate">{category.label}</span>
                  </Button>
                );
              })}
            </div>
            <label className="relative block min-w-0">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input
                aria-label="Search project materials"
                className="pl-9"
                value={materialSearch}
                onChange={(event) => setMaterialSearch(event.target.value)}
                placeholder={ui(`Search ${materialFilter} materials`)}
              />
            </label>
          </div>
          {liveRefresh.state === 'stale' ? (
            <DataState state="warning" title="Materials may be stale" message="Last successful material list is still visible while live refresh retries." />
          ) : null}
          {materialsQuery.isLoading ? <DataState state="loading" title="Loading materials" message="Loading project materials." /> : null}
          {materialsQuery.error ? <DataState state="error" title="Materials unavailable" message={materialsQuery.error.message} /> : null}
          {!materialsQuery.isLoading && !filteredMaterials.length ? (
            <DataState state="empty" title="No matching materials" message={ui(`No ${materialFilter} materials match the current search.`)} />
          ) : null}
          <ul className="mt-4 grid min-h-0 gap-3 overflow-y-auto pr-1" aria-label={ui(`${materialFilter} material results`)}>
            {filteredMaterials.map((material) => (
              <li key={material.id} className="rounded-md border p-3">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <strong>{material.displayName || `${ui(material.materialType)} ${material.backingRecordId}`}</strong>
                  <span className="flex flex-wrap gap-2">
                    <VisibilityStateBadge visibility={material.visibility} />
                    <SourceProjectBadge title={material.sourceProject.title} />
                  </span>
                </div>
                <p className="text-sm capitalize text-muted-foreground">
                  {ui(`${material.materialType} · ${material.classificationState.replaceAll('_', ' ')}`)}
                </p>
                {material.actionCapabilities.canDownload || material.actionCapabilities.canChangeVisibility ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      aria-label={ui(`Download ${material.displayName || `${material.materialType} ${material.backingRecordId}`}`)}
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
