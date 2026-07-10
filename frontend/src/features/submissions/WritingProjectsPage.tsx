import { FileUp, Plus } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useParams } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Textarea } from '@/shared/ui/primitives/textarea';

import { DataState } from '../../shared/ui/DataState';
import { LocalizedValidation } from '../../shared/ui/LocalizedValidation';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { TeacherFeedbackPanel } from './TeacherFeedbackPanel';
import { WritingVersionHistory } from './WritingVersionHistory';
import {
  useCreateWritingProject,
  useUploadWritingVersion,
  useWritingProjects,
  type WritingProject,
  type WritingVersion,
} from './api';

function WritingProjectCreateForm({ projectId }: { projectId?: number }) {
  const [title, setTitle] = useState('');
  const [writingType, setWritingType] = useState<WritingProject['writingType']>('thesis');
  const [error, setError] = useState('');
  const createMutation = useCreateWritingProject(projectId);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      await createMutation.mutateAsync({ title, writingType });
      setTitle('');
      setWritingType('thesis');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Writing project creation failed');
    }
  }

  return (
    <form className="grid gap-2 rounded-md border p-3" onSubmit={onSubmit}>
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
      <LocalizedValidation message={error} />
    </form>
  );
}

function WritingVersionUploadForm({ projectId, writingProject }: { projectId?: number; writingProject?: WritingProject }) {
  const [file, setFile] = useState<File | undefined>();
  const [summary, setSummary] = useState('');
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const uploadMutation = useUploadWritingVersion(projectId, writingProject?.id ?? '');

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!writingProject || !file) return;
    setSuccess('');
    setError('');
    try {
      await uploadMutation.mutateAsync({ file, summary });
      setFile(undefined);
      setSummary('');
      setSuccess('Version uploaded');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Version upload failed');
    }
  }

  return (
    <form className="grid gap-3 rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <UploadRequirements title="Word or LaTeX version upload" extensions={['.doc', '.docx', '.tex', '.zip', '.tar', '.gz', '.tgz']} maxSizeLabel="50 MB" />
      <Input
        aria-label="Writing version file"
        type="file"
        accept=".doc,.docx,.tex,.zip,.tar,.gz,.tgz,application/zip,application/gzip,application/x-tar"
        onChange={(event) => setFile(event.target.files?.[0])}
        disabled={!writingProject}
        required
      />
      <Textarea aria-label="Version summary" value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Version summary" />
      <Button type="submit" disabled={!writingProject || !file || uploadMutation.isPending}>
        <FileUp className="h-4 w-4" aria-hidden="true" />
        Upload version
      </Button>
      {uploadMutation.isPending ? <UploadProgress label="Uploading version" value={65} /> : null}
      <LocalizedValidation message={error} />
      {success ? <p role="status" className="text-sm font-medium text-success">{success}</p> : null}
    </form>
  );
}

export function WritingProjectsPage() {
  const projectIdParam = useParams().projectId;
  const projectId = projectIdParam ? Number(projectIdParam) : undefined;
  const [query, setQuery] = useState('');
  const [selectedProject, setSelectedProject] = useState<WritingProject | undefined>();
  const [selectedVersion, setSelectedVersion] = useState<WritingVersion | undefined>();
  const writingQuery = useWritingProjects(projectId, query);
  const projects = writingQuery.data?.results ?? [];
  const activeProject = projects.find((project) => project.id === selectedProject?.id) ?? projects[0];
  const activeVersion = activeProject?.versions.find((version) => version.id === selectedVersion?.id) ?? activeProject?.versions?.[0];

  function selectProject(project: WritingProject) {
    setSelectedProject(project);
    setSelectedVersion(project.versions[0]);
  }

  return (
    <PageShell title="Writing projects" description="Manage standalone student-teacher writing histories, version uploads, advisor annotations, and feedback downloads.">
      <div className="grid gap-4 xl:grid-cols-[minmax(22rem,1fr)_minmax(22rem,0.85fr)]">
        <section className="panel" aria-label="Writing projects">
          <div className="mb-4 grid gap-3">
            <Input aria-label="Search writing projects" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search writing projects" />
            <WritingProjectCreateForm projectId={projectId} />
          </div>
          {writingQuery.isLoading ? <DataState state="loading" title="Loading writing projects" message="Loading writing histories." /> : null}
          {writingQuery.error ? <DataState state="error" title="Writing projects failed" message={writingQuery.error.message} /> : null}
          {!writingQuery.isLoading && !projects.length ? <DataState state="empty" title="No writing projects" message="Create a writing project before uploading versions." /> : null}
          <ul className="grid gap-2">
            {projects.map((project) => (
              <li key={project.id}>
                <button
                  type="button"
                  aria-label={`Select writing project ${project.title}`}
                  className="w-full rounded-md border p-3 text-left hover:bg-muted"
                  onClick={() => selectProject(project)}
                >
                  <span className="mb-2 flex flex-wrap items-start justify-between gap-2">
                    <strong>{project.title}</strong>
                    <StatusBadge status={project.status} />
                  </span>
                  <span className="block text-sm capitalize text-muted-foreground">
                    {project.writingType} · {project.versions.length} version{project.versions.length === 1 ? '' : 's'}
                  </span>
                  {project.participantRole ? (
                    <span className="mt-2 block text-sm text-muted-foreground">
                      Role: {project.participantRole.replaceAll('_', ' ')}
                    </span>
                  ) : null}
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel" aria-label="Writing project detail">
          {activeProject ? (
            <div className="grid gap-4">
              <div>
                <h2 className="text-lg font-semibold">{activeProject.title}</h2>
                <p className="text-sm capitalize text-muted-foreground">{activeProject.writingType}</p>
              </div>
              {activeProject.participantRole === 'student_author' || activeProject.participantRole === 'administrator' ? (
                <WritingVersionUploadForm projectId={projectId} writingProject={activeProject} />
              ) : (
                <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
                  Version uploads are available to the student author.
                </p>
              )}
              <WritingVersionHistory versions={activeProject.versions} selectedVersionId={activeVersion?.id} onSelectVersion={setSelectedVersion} />
              <TeacherFeedbackPanel projectId={projectId} version={activeVersion} />
            </div>
          ) : (
            <DataState state="empty" title="Select writing project" message="Writing project details appear after a project is selected." />
          )}
        </section>
      </div>
    </PageShell>
  );
}
