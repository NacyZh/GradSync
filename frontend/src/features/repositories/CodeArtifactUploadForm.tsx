import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { LocalizedValidation } from '../../shared/ui/LocalizedValidation';
import { useCreateCodeArtifact, useUploadCodeVersion } from './api';

export function CodeArtifactUploadForm({ projectId }: { projectId: number }) {
  const [artifactId, setArtifactId] = useState('');
  const [name, setName] = useState('');
  const [versionLabel, setVersionLabel] = useState('');
  const [filename, setFilename] = useState('source.zip');
  const [checksum, setChecksum] = useState('0'.repeat(64));
  const [error, setError] = useState('');
  const createArtifact = useCreateCodeArtifact(projectId);
  const uploadVersion = useUploadCodeVersion(projectId, artifactId);

  async function onCreate(event: React.FormEvent) {
    event.preventDefault();
    setError('');
    try {
      const artifact = await createArtifact.mutateAsync({ name, tags: ['research'] });
      setArtifactId(artifact.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create artifact');
    }
  }

  async function onUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!artifactId) return;
    setError('');
    try {
      await uploadVersion.mutateAsync({ versionLabel, filename, checksumSha256: checksum, contentType: 'application/zip', sizeBytes: 1024 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Version conflict');
    }
  }

  return (
    <div className="grid gap-4">
      <form className="grid gap-2" onSubmit={onCreate}>
        <Input aria-label="Artifact name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Artifact name" required />
        <Button type="submit">Create artifact</Button>
      </form>
      <form className="grid gap-2" onSubmit={onUpload}>
        <Input aria-label="Version label" value={versionLabel} onChange={(event) => setVersionLabel(event.target.value)} placeholder="Version label" />
        <Input aria-label="Archive filename" value={filename} onChange={(event) => setFilename(event.target.value)} placeholder="source.zip" />
        <Input aria-label="Checksum" value={checksum} onChange={(event) => setChecksum(event.target.value)} placeholder="sha256" />
        <Button type="submit" disabled={!artifactId}>Upload version</Button>
      </form>
      <LocalizedValidation message={error} />
    </div>
  );
}
