import { FileText, FileUp, FolderOpen, Pencil, Plus, Trash2, X } from 'lucide-react';
import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { uploadSizeError, useUploadPolicy } from '@/shared/api/uploadPolicy';

import { getErrorMessage } from '../../shared/api/errors';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { useAuth } from '../auth/AuthProvider';
import { TeacherFeedbackPanel } from './TeacherFeedbackPanel';
import { WritingVersionHistory } from './WritingVersionHistory';
import {
  useCreateWritingProject,
  useDeleteWritingProject,
  useRenameWritingProject,
  useUploadWritingVersion,
  useWritingProjects,
  type WritingProject,
  type WritingVersion,
} from './api';

function WritingProjectCreateForm({ projectId }: { projectId?: number }) {
  const [title, setTitle] = useState('');
  const [writingType, setWritingType] = useState<WritingProject['writingType']>('thesis');
  const { notify } = useAppFeedback();
  const createMutation = useCreateWritingProject(projectId);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await createMutation.mutateAsync({ title, writingType });
      setTitle('');
      setWritingType('thesis');
      notify('Writing project created', 'success');
    } catch (err) {
      const message = getErrorMessage(err);
      notify(message, 'error');
    }
  }

  return (
    <form className="grid gap-2 rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <div className="grid gap-2 sm:grid-cols-[1fr_10rem]">
        <Input aria-label="Writing project title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Writing project title" required />
        <select
          aria-label="Writing type"
          className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={writingType}
          onChange={(event) => setWritingType(event.target.value as WritingProject['writingType'])}
        >
          <option value="thesis">Thesis</option>
          <option value="manuscript">Manuscript</option>
          <option value="paper">Paper</option>
          <option value="other">Other</option>
        </select>
      </div>
      <Button type="submit" disabled={!title.trim() || createMutation.isPending}>
        <Plus className="h-4 w-4" aria-hidden="true" />
        Create writing project
      </Button>
    </form>
  );
}

function WritingVersionUploadForm({ projectId, writingProject }: { projectId?: number; writingProject?: WritingProject }) {
  const [file, setFile] = useState<File | undefined>();
  const [summary, setSummary] = useState('');
  const { notify } = useAppFeedback();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadWritingVersion(projectId, writingProject?.id ?? '');
  const uploadPolicyQuery = useUploadPolicy('writing');

  function clearFile() {
    setFile(undefined);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!writingProject || !file) return;
    const sizeError = uploadSizeError(file, uploadPolicyQuery.data);
    if (sizeError) {
      notify(sizeError, 'error');
      return;
    }
    try {
      await uploadMutation.mutateAsync({ file, summary });
      clearFile();
      setSummary('');
      notify('Version uploaded', 'success');
    } catch (err) {
      const message = getErrorMessage(err);
      notify(message, 'error');
    }
  }

  return (
    <form className="grid gap-3 rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <UploadRequirements
        title="Word or LaTeX version upload"
        extensions={uploadPolicyQuery.data?.allowedExtensions ?? ['.doc', '.docx', '.tex', '.zip', '.tar', '.gz', '.tgz']}
        maxSizeLabel={uploadPolicyQuery.data?.displayLabel ?? 'Loading limit'}
      />
      <input
        ref={fileInputRef}
        className="hidden"
        aria-label="Writing version file"
        type="file"
        accept=".doc,.docx,.tex,.zip,.tar,.gz,.tgz,application/zip,application/gzip,application/x-tar"
        onChange={(event) => setFile(event.target.files?.[0])}
        disabled={!writingProject}
        required
      />
      <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
        <Button
          type="button"
          variant="outline"
          className="min-w-0"
          onClick={() => fileInputRef.current?.click()}
          disabled={!writingProject}
          aria-label={file ? 'Reselect version' : 'Choose version'}
        >
          <FolderOpen className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span className="truncate">{file ? 'Reselect file' : 'Choose file'}</span>
        </Button>
        {file ? (
          <Button type="button" variant="ghost" className="min-w-0" onClick={clearFile} aria-label="Clear writing version file">
            <X className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="truncate">Clear</span>
          </Button>
        ) : null}
      </div>
      {file ? <p className="min-w-0 truncate text-sm text-muted-foreground">Selected file: {file.name}</p> : null}
      <Textarea aria-label="Version summary" value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Version summary" />
      <Button type="submit" disabled={!writingProject || !file || uploadMutation.isPending}>
        <FileUp className="h-4 w-4" aria-hidden="true" />
        Upload version
      </Button>
      {uploadMutation.isPending ? <UploadProgress label="Uploading version" value={65} /> : null}
    </form>
  );
}

function formatWritingProjectTitle(project: WritingProject) {
  const title = project.title.trim();
  if (!title) return `Writing project ${project.id}`;
  return /^\d+$/.test(title) ? `Writing project ${title}` : title;
}

function formatLabel(value: string | undefined) {
  return value ? value.replaceAll('_', ' ') : '';
}

export function WritingProjectsPage() {
  const { user } = useAuth();
  const projectIdParam = useParams().projectId;
  const [searchParams] = useSearchParams();
  const projectId = projectIdParam ? Number(projectIdParam) : undefined;
  const requestedWritingProjectId = searchParams.get('writingProjectId');
  const [query, setQuery] = useState('');
  const [selectedProject, setSelectedProject] = useState<WritingProject | undefined>();
  const [selectedVersion, setSelectedVersion] = useState<WritingVersion | undefined>();
  const [renamedProjects, setRenamedProjects] = useState<Record<string, WritingProject>>({});
  const [archivedProjectIds, setArchivedProjectIds] = useState<Set<string>>(() => new Set());
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameTitle, setRenameTitle] = useState('');
  const { notify } = useAppFeedback();
  const writingQuery = useWritingProjects(projectId, query);
  const renameMutation = useRenameWritingProject(projectId);
  const deleteMutation = useDeleteWritingProject(projectId);
  const projects = (writingQuery.data?.results ?? [])
    .map((project) => renamedProjects[project.id] ?? project)
    .filter((project) => !archivedProjectIds.has(project.id));
  const activeProject = projects.find((project) => project.id === selectedProject?.id)
    ?? projects.find((project) => project.id === requestedWritingProjectId)
    ?? projects[0];
  const activeVersion = activeProject?.versions.find((version) => version.id === selectedVersion?.id) ?? activeProject?.versions?.[0];
  const canCreateWritingProject = !user || user.global_role === 'student';
  const canManageActiveProject = activeProject?.participantRole === 'student_author'
    || activeProject?.participantRole === 'administrator';

  function selectProject(project: WritingProject) {
    setSelectedProject(project);
    setSelectedVersion(project.versions[0]);
    setIsRenaming(false);
  }

  function startRename(project: WritingProject) {
    setRenameTitle(project.title);
    setIsRenaming(true);
  }

  async function saveRename() {
    if (!activeProject) return;
    try {
      const renamed = await renameMutation.mutateAsync({
        writingProjectId: activeProject.id,
        title: renameTitle,
      });
      setRenamedProjects((current) => ({ ...current, [renamed.id]: renamed }));
      setSelectedProject(renamed);
      setIsRenaming(false);
      notify('Writing project renamed', 'success');
    } catch (err) {
      const message = getErrorMessage(err);
      notify(message, 'error');
    }
  }

  async function deleteActiveProject() {
    if (!activeProject) return;
    if (!window.confirm(`Delete ${formatWritingProjectTitle(activeProject)}?`)) return;
    try {
      await deleteMutation.mutateAsync(activeProject.id);
      setArchivedProjectIds((current) => new Set(current).add(activeProject.id));
      setSelectedProject(undefined);
      setSelectedVersion(undefined);
      setIsRenaming(false);
      notify('Writing project deleted', 'success');
    } catch (err) {
      const message = getErrorMessage(err);
      notify(message, 'error');
    }
  }

  return (
    <PageShell title="Writing projects" description="Manage standalone student-teacher writing histories, version uploads, advisor annotations, and feedback downloads.">
      <div className="grid gap-4 xl:grid-cols-[minmax(22rem,1fr)_minmax(22rem,0.85fr)]">
        <section className="panel" aria-label="Writing projects">
          <div className="mb-4 grid gap-3">
            <Input aria-label="Search writing projects" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search writing projects" />
            {canCreateWritingProject ? <WritingProjectCreateForm projectId={projectId} /> : null}
          </div>
          {writingQuery.isLoading ? <DataState state="loading" title="Loading writing projects" message="Loading writing histories." /> : null}
          {writingQuery.error ? <DataState state="error" title="Writing projects failed" message={writingQuery.error.message} /> : null}
          {!writingQuery.isLoading && !projects.length ? <DataState state="empty" title="No writing projects" message="Create a writing project before uploading versions." /> : null}
          <ul className="grid gap-2">
            {projects.map((project) => (
              <li key={project.id}>
                <button
                  type="button"
                  aria-label={`Select writing project ${formatWritingProjectTitle(project)}`}
                  className="w-full rounded-md border p-3 text-left hover:bg-muted data-[selected=true]:border-primary data-[selected=true]:bg-muted/60"
                  data-selected={activeProject?.id === project.id}
                  onClick={() => selectProject(project)}
                >
                  <span className="mb-2 flex min-w-0 items-start gap-3">
                    <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-background">
                      <FileText className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-start justify-between gap-2">
                        <strong className="min-w-0 break-words">{formatWritingProjectTitle(project)}</strong>
                        <StatusBadge status={project.status} />
                      </span>
                      <span className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span className="rounded-md border px-2 py-1 capitalize">{formatLabel(project.writingType)}</span>
                        <span className="rounded-md border px-2 py-1">
                          {project.versions.length} version{project.versions.length === 1 ? '' : 's'}
                        </span>
                        {project.participantRole ? (
                          <span className="rounded-md border px-2 py-1 capitalize">
                            {formatLabel(project.participantRole)}
                          </span>
                        ) : null}
                      </span>
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel" aria-label="Writing project detail">
          {activeProject ? (
            <div className="grid gap-4">
              <div>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="min-w-0 break-words text-lg font-semibold">{formatWritingProjectTitle(activeProject)}</h2>
                    <p className="text-sm capitalize text-muted-foreground">{formatLabel(activeProject.writingType)}</p>
                  </div>
                  {canManageActiveProject ? (
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" variant="outline" size="sm" onClick={() => startRename(activeProject)}>
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                        Rename
                      </Button>
                      <Button type="button" variant="destructive" size="sm" onClick={deleteActiveProject} disabled={deleteMutation.isPending}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        Delete
                      </Button>
                    </div>
                  ) : null}
                </div>
                {isRenaming ? (
                  <div className="mt-3 grid gap-2 rounded-md border p-3">
                    <Input
                      aria-label="Rename writing project"
                      value={renameTitle}
                      onChange={(event) => setRenameTitle(event.target.value)}
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" size="sm" onClick={saveRename} disabled={!renameTitle.trim() || renameMutation.isPending}>
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                        Save rename
                      </Button>
                      <Button type="button" variant="ghost" size="sm" onClick={() => setIsRenaming(false)}>
                        <X className="h-4 w-4" aria-hidden="true" />
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : null}
              </div>
              {activeProject.participantRole === 'student_author' ? (
                <WritingVersionUploadForm projectId={projectId} writingProject={activeProject} />
              ) : (
                <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
                  Version uploads are available to the student author.
                </p>
              )}
              <WritingVersionHistory versions={activeProject.versions} selectedVersionId={activeVersion?.id} onSelectVersion={setSelectedVersion} />
              <TeacherFeedbackPanel participantRole={activeProject.participantRole} projectId={projectId} version={activeVersion} />
            </div>
          ) : (
            <DataState state="empty" title="Select writing project" message="Writing project details appear after a project is selected." />
          )}
        </section>
      </div>
    </PageShell>
  );
}
