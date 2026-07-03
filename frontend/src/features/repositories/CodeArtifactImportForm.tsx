import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { LocalizedValidation } from '../../shared/ui/LocalizedValidation';
import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { useCodeArtifactUpload } from './api';

export function CodeArtifactImportForm({ projectId }: { projectId: number }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [visibility, setVisibility] = useState<'project_members' | 'group_wide'>('project_members');
  const [archive, setArchive] = useState<File | undefined>();
  const [uploadComplete, setUploadComplete] = useState(false);
  const [error, setError] = useState('');
  const uploadMutation = useCodeArtifactUpload(projectId);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget as HTMLFormElement);
    const selectedArchive = archive ?? formData.get('archive');
    if (!(selectedArchive instanceof File)) return;
    setError('');
    setUploadComplete(false);
    try {
      await uploadMutation.mutateAsync({
        archive: selectedArchive,
        name,
        description,
        tags,
        visibility,
      });
      setUploadComplete(true);
      setName('');
      setDescription('');
      setTags('');
      setArchive(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Archive upload failed');
    }
  }

  return (
    <form className="grid gap-3 rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <UploadRequirements title="Code archive upload" extensions={['.zip', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.7z']} maxSizeLabel="100 MB" />
      <Input
        aria-label="Archive file"
        name="archive"
        type="file"
        accept=".zip,.tar,.gz,.tgz,.bz2,.xz,.7z,application/zip,application/gzip,application/x-tar"
        onChange={(event) => setArchive(event.target.files?.[0])}
        required
      />
      <div className="grid gap-2 sm:grid-cols-2">
        <Input aria-label="Artifact name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Artifact name" required />
        <Input aria-label="Tags" value={tags} onChange={(event) => setTags(event.target.value)} placeholder="simulation, python" />
      </div>
      <Input
        aria-label="Artifact description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder="Searchable archive description"
        required
      />
      <select
        aria-label="Code archive visibility"
        className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        value={visibility}
        onChange={(event) => setVisibility(event.target.value as 'project_members' | 'group_wide')}
      >
        <option value="project_members">Project members</option>
        <option value="group_wide">Group wide</option>
      </select>
      <Button type="submit" disabled={uploadMutation.isPending}>Upload archive</Button>
      {uploadMutation.isPending ? <UploadProgress label="Uploading archive" value={65} /> : null}
      <LocalizedValidation message={error} />
      {uploadComplete ? <p role="status" className="text-sm font-medium text-success">Upload complete</p> : null}
    </form>
  );
}
