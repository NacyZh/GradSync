import { useMutation, useQuery } from '@tanstack/react-query';
import { MessageSquarePlus } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { FieldGroup, FormField, TextareaField } from '../../shared/ui/FormField';
import { createComment, listComments } from './api';
import { CommentThread } from './CommentThread';

export function InlineCommentPanel({ projectId, targetType, targetId, disabled = false }: { projectId?: number; targetType?: string; targetId?: number; disabled?: boolean }) {
  const { notify } = useAppFeedback();
  const commentsQuery = useQuery({
    queryKey: ['comments', projectId, targetType, targetId],
    queryFn: () => listComments(projectId ?? 0, targetType, targetId),
    enabled: Boolean(projectId),
  });
  const mutation = useMutation({
    mutationFn: (payload: { anchor: string; body: string }) =>
      createComment(projectId ?? 0, { target_type: targetType ?? 'draft_version', target_id: targetId ?? 0, ...payload }),
    onSuccess: () => {
      notify('Comment added', 'success');
      commentsQuery.refetch();
    },
    onError: (error) => notify(error.message, 'error'),
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({ anchor: String(form.get('anchor') ?? 'general'), body: String(form.get('body')) });
  }

  return (
    <aside className="panel comment-panel" aria-label="Inline comments">
      <h2 className="flex items-center gap-2">
        <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
        Inline comments
      </h2>
      <p className="mb-4 text-sm text-muted-foreground">
        Target: {targetType ?? 'draft_version'} #{targetId ?? 'not selected'}
      </p>
      {!targetId ? <DataState state="warning" title="No review target" message="Select a draft version or progress report before adding anchored comments." /> : null}
      <CommentThread projectId={projectId} comments={commentsQuery.data?.results ?? []} />
      <form className="stacked-form" onSubmit={onSubmit}>
        <FieldGroup>
          <FormField id="comment-anchor" name="anchor" label="Page or section anchor" defaultValue="general" disabled={disabled || !targetId || mutation.isPending} />
          <TextareaField id="comment-body" name="body" label="Comment" required disabled={disabled || !targetId || mutation.isPending} />
        </FieldGroup>
        <Button type="submit" disabled={disabled || !targetId || mutation.isPending}>Add comment</Button>
        {disabled ? <p className="text-sm text-muted-foreground">Comments are disabled for archived or unauthorized targets.</p> : null}
      </form>
    </aside>
  );
}
