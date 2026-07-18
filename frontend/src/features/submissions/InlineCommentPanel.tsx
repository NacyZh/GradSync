import { useMutation, useQuery } from '@tanstack/react-query';
import { MessageSquarePlus } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { FieldGroup, FormField, TextareaField } from '../../shared/ui/FormField';
import { createComment, listComments } from './api';
import { CommentThread } from './CommentThread';

export function InlineCommentPanel({
  projectId,
  targetType = 'progress_report',
  targetId,
  targetLabel,
  disabled = false,
}: {
  projectId?: number;
  targetType?: string;
  targetId?: number;
  targetLabel?: string;
  disabled?: boolean;
}) {
  const { notify } = useAppFeedback();
  const commentsQuery = useQuery({
    queryKey: ['comments', projectId, targetType, targetId],
    queryFn: () => listComments(projectId ?? 0, targetType, targetId),
    enabled: Boolean(projectId && targetId),
  });
  const mutation = useMutation({
    mutationFn: (payload: { anchor: string; body: string }) =>
      createComment(projectId ?? 0, { target_type: targetType, target_id: targetId ?? 0, ...payload }),
    onSuccess: () => {
      notify('Comment added', 'success');
      commentsQuery.refetch();
    },
    onError: (error) => notify(error.message, 'error'),
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!targetId) return;
    const form = new FormData(event.currentTarget);
    mutation.mutate({ anchor: String(form.get('anchor') ?? 'general'), body: String(form.get('body')) });
    event.currentTarget.reset();
  }

  return (
    <aside className="panel comment-panel grid min-h-[28rem] min-w-0 grid-rows-[auto_auto_1fr_auto] overflow-hidden" aria-label="Inline comments">
      <h2 className="flex items-center gap-2">
        <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
        Inline comments
      </h2>
      <p className="mb-4 text-sm text-muted-foreground">
        {targetId ? `Linked to ${targetLabel ?? `${targetType} #${targetId}`}` : 'Select a report to load its comments.'}
      </p>
      {!targetId ? <DataState state="warning" title="No review target" message="Select a progress report before adding anchored comments." /> : null}
      {targetId && commentsQuery.isLoading ? <DataState state="loading" message="Loading comments" /> : null}
      {targetId && !commentsQuery.isLoading ? (
        <CommentThread
          projectId={projectId}
          comments={commentsQuery.data?.results ?? []}
          onStatusChanged={() => commentsQuery.refetch()}
        />
      ) : null}
      <form className="stacked-form mt-4 border-t pt-4" onSubmit={onSubmit}>
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
