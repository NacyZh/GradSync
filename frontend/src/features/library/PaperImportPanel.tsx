import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { UploadProgress } from '../../shared/ui/UploadProgress';
import { usePaperImport, type PaperImportBatch } from './api';
import { DuplicateReviewPanel } from './DuplicateReviewPanel';

export function PaperImportPanel({ projectId }: { projectId: number }) {
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [batch, setBatch] = useState<PaperImportBatch | undefined>();
  const importMutation = usePaperImport(projectId);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const result = await importMutation.mutateAsync([{ title, authors: [author || 'Unknown'] }]);
    setBatch(result);
  }

  return (
    <form className="grid gap-3" onSubmit={onSubmit}>
      <div className="grid gap-2 sm:grid-cols-2">
        <Input aria-label="Paper title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Paper title" required />
        <Input aria-label="First author" value={author} onChange={(event) => setAuthor(event.target.value)} placeholder="First author" />
      </div>
      <Button type="submit" disabled={importMutation.isPending}>Import</Button>
      {importMutation.isPending ? <UploadProgress label="Importing papers" value={65} /> : null}
      <DuplicateReviewPanel batch={batch} />
    </form>
  );
}
