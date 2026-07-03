import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { LocalImportProgress, UploadProgress } from '../../shared/ui/UploadProgress';
import { usePaperImport, usePaperUpload, type PaperImportBatch } from './api';
import { DuplicateReviewPanel } from './DuplicateReviewPanel';

export function PaperImportPanel({ projectId }: { projectId: number }) {
  const [sourcePathLabel, setSourcePathLabel] = useState('team-library/papers');
  const [title, setTitle] = useState('');
  const [authors, setAuthors] = useState('');
  const [publicationYear, setPublicationYear] = useState('');
  const [keywords, setKeywords] = useState('');
  const [visibility, setVisibility] = useState<'project_members' | 'group_wide'>('project_members');
  const [file, setFile] = useState<File | undefined>();
  const [uploadComplete, setUploadComplete] = useState(false);
  const [batch, setBatch] = useState<PaperImportBatch | undefined>();
  const importMutation = usePaperImport(projectId);
  const uploadMutation = usePaperUpload(projectId);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget as HTMLFormElement);
    const selectedFile = file ?? formData.get('file');
    if (!(selectedFile instanceof File)) return;
    setUploadComplete(false);
    await uploadMutation.mutateAsync({
      file: selectedFile,
      title,
      authors,
      publicationYear,
      keywords,
      visibility,
    });
    setUploadComplete(true);
    setTitle('');
    setAuthors('');
    setPublicationYear('');
    setKeywords('');
    setFile(undefined);
  }

  async function onStageMetadataImport() {
    const result = await importMutation.mutateAsync({
      sourcePathLabel,
      items: [{ title: title || 'Untitled paper', authors: [authors || 'Unknown'], sourcePathLabel }],
    });
    setBatch(result);
  }

  return (
    <form className="grid gap-3 rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <UploadRequirements title="PDF paper upload" extensions={['.pdf']} maxSizeLabel="25 MB" />
      <Input
        aria-label="PDF file"
        name="file"
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => setFile(event.target.files?.[0])}
        required
      />
      <div className="grid gap-2 sm:grid-cols-2">
        <Input aria-label="Paper title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Paper title" required />
        <Input aria-label="Authors" value={authors} onChange={(event) => setAuthors(event.target.value)} placeholder="Ada Lovelace, Grace Hopper" required />
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <Input aria-label="Publication year" value={publicationYear} onChange={(event) => setPublicationYear(event.target.value)} placeholder="2026" inputMode="numeric" />
        <Input aria-label="Keywords" value={keywords} onChange={(event) => setKeywords(event.target.value)} placeholder="systems, collaboration" />
        <select
          aria-label="Paper visibility"
          className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={visibility}
          onChange={(event) => setVisibility(event.target.value as 'project_members' | 'group_wide')}
        >
          <option value="project_members">Project members</option>
          <option value="group_wide">Group wide</option>
        </select>
      </div>
      <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
        <Input aria-label="Local source label" value={sourcePathLabel} onChange={(event) => setSourcePathLabel(event.target.value)} placeholder="team-library/papers" />
        <Button type="button" variant="outline" onClick={onStageMetadataImport} disabled={importMutation.isPending}>Stage metadata</Button>
      </div>
      <Button type="submit" disabled={uploadMutation.isPending}>Upload paper</Button>
      {uploadMutation.isPending ? <UploadProgress label="Uploading paper" value={65} /> : null}
      {importMutation.isPending ? <LocalImportProgress label="Importing papers" value={65} /> : null}
      {uploadMutation.error ? <p role="alert" className="text-sm font-medium text-destructive">{uploadMutation.error.message}</p> : null}
      {uploadComplete ? <p role="status" className="text-sm font-medium text-success">Upload complete</p> : null}
      <DuplicateReviewPanel batch={batch} />
    </form>
  );
}
