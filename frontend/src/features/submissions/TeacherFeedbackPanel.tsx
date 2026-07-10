import { MessageSquare, Send } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Textarea } from '@/shared/ui/primitives/textarea';

import { LocalizedValidation } from '../../shared/ui/LocalizedValidation';
import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { FeedbackDownloadList } from './WritingVersionHistory';
import { useSubmitTeacherFeedback, type WritingVersion } from './api';

export function TeacherFeedbackPanel({ projectId, version }: { projectId?: number; version?: WritingVersion }) {
  const [comments, setComments] = useState('');
  const [annotatedFile, setAnnotatedFile] = useState<File | undefined>();
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const feedbackMutation = useSubmitTeacherFeedback(projectId, version?.id ?? '');

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!version || !annotatedFile) return;
    setSuccess('');
    setError('');
    try {
      await feedbackMutation.mutateAsync({ annotatedFile, comments });
      setComments('');
      setAnnotatedFile(undefined);
      setSuccess('Feedback saved and notification recorded');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Feedback submission failed');
    }
  }

  if (!version) {
    return <p className="text-sm text-muted-foreground">Select a version to review feedback.</p>;
  }

  return (
    <div className="grid gap-4" aria-label="Teacher feedback">
      <div>
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <MessageSquare className="h-4 w-4" aria-hidden="true" />
          Review version {version.versionNumber}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">{version.draftFileName ?? 'Draft file'} · {version.status.replaceAll('_', ' ')}</p>
      </div>
      <FeedbackDownloadList feedback={version.feedback ?? []} />
      <form className="grid gap-3 rounded-md border p-3" onSubmit={onSubmit} noValidate>
        <UploadRequirements title="Annotated feedback upload" extensions={['.pdf', '.doc', '.docx', '.txt', '.md']} maxSizeLabel="25 MB" />
        <Input
          aria-label="Annotated file"
          type="file"
          accept=".pdf,.doc,.docx,.txt,.md,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
          onChange={(event) => setAnnotatedFile(event.target.files?.[0])}
          required
        />
        <Textarea
          aria-label="Feedback comments"
          value={comments}
          onChange={(event) => setComments(event.target.value)}
          placeholder="Review comments"
        />
        <Button type="submit" disabled={!annotatedFile || feedbackMutation.isPending}>
          <Send className="h-4 w-4" aria-hidden="true" />
          Submit feedback
        </Button>
        {feedbackMutation.isPending ? <UploadProgress label="Uploading feedback" value={70} /> : null}
        <LocalizedValidation message={error} />
        {success ? <p role="status" className="text-sm font-medium text-success">{success}</p> : null}
      </form>
    </div>
  );
}
