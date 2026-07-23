import { FileUp, MessageSquare, Send, X } from 'lucide-react';
import { useRef, useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { uploadSizeError, useUploadPolicy } from '@/shared/api/uploadPolicy';

import { getErrorMessage } from '../../shared/api/errors';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { FeedbackDownloadList } from './WritingVersionHistory';
import { useSubmitTeacherFeedback, type WritingProject, type WritingVersion } from './api';

type TeacherFeedbackPanelProps = {
  participantRole?: WritingProject['participantRole'];
  projectId?: number;
  version?: WritingVersion;
};

export function TeacherFeedbackPanel({ participantRole, projectId, version }: TeacherFeedbackPanelProps) {
  const [comments, setComments] = useState('');
  const [annotatedFile, setAnnotatedFile] = useState<File | undefined>();
  const { notify } = useAppFeedback();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const feedbackMutation = useSubmitTeacherFeedback(projectId, version?.id ?? '');
  const uploadPolicyQuery = useUploadPolicy('feedback');
  const canSubmitFeedback = participantRole === 'bound_advisor'
    || participantRole === 'assigned_reviewer'
    || participantRole === 'administrator';

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!version || !annotatedFile || !canSubmitFeedback) return;
    const sizeError = uploadSizeError(annotatedFile, uploadPolicyQuery.data);
    if (sizeError) {
      notify(sizeError, 'error');
      return;
    }
    try {
      await feedbackMutation.mutateAsync({ annotatedFile, comments });
      setComments('');
      setAnnotatedFile(undefined);
      if (fileInputRef.current) fileInputRef.current.value = '';
      notify('Feedback saved and notification recorded', 'success');
    } catch (err) {
      const message = getErrorMessage(err);
      notify(message, 'error');
    }
  }

  function clearAnnotatedFile() {
    setAnnotatedFile(undefined);
    if (fileInputRef.current) fileInputRef.current.value = '';
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
      {!canSubmitFeedback ? (
        <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
          Feedback submission is available to assigned reviewers and advisors.
        </p>
      ) : null}
      {canSubmitFeedback ? (
      <form className="grid gap-3 rounded-md border p-3" onSubmit={onSubmit} noValidate>
        <UploadRequirements
          title="Annotated feedback upload"
          extensions={uploadPolicyQuery.data?.allowedExtensions ?? ['.pdf', '.doc', '.docx', '.txt', '.md']}
          maxSizeLabel={uploadPolicyQuery.data?.displayLabel ?? 'Loading limit'}
        />
        <Input
          ref={fileInputRef}
          className="sr-only"
          aria-label="Annotated file"
          type="file"
          accept=".pdf,.doc,.docx,.txt,.md,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
          onChange={(event) => setAnnotatedFile(event.target.files?.[0])}
          required
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()} aria-label="Choose feedback file">
            <FileUp className="h-4 w-4" aria-hidden="true" />
            Choose file
          </Button>
          {annotatedFile ? (
            <Button type="button" variant="ghost" onClick={clearAnnotatedFile} aria-label="Clear annotated file">
              <X className="h-4 w-4" aria-hidden="true" />
              Clear
            </Button>
          ) : null}
        </div>
        {annotatedFile ? (
          <p className="min-w-0 break-words text-sm text-muted-foreground">
            Selected file: {annotatedFile.name}
          </p>
        ) : null}
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
      </form>
      ) : null}
    </div>
  );
}
