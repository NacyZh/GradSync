import { useMutation, useQuery } from '@tanstack/react-query';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { createComment, listComments } from './api';
import { CommentThread } from './CommentThread';

export function InlineCommentPanel({ projectId, targetType, targetId }: { projectId?: number; targetType?: string; targetId?: number }) {
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
      <h2>Inline comments</h2>
      <CommentThread projectId={projectId} comments={commentsQuery.data?.results ?? []} />
      <form className="stacked-form" onSubmit={onSubmit}>
        <label>
          Page or section anchor
          <input name="anchor" defaultValue="general" />
        </label>
        <label>
          Comment
          <textarea name="body" />
        </label>
        <button type="submit">Add comment</button>
      </form>
    </aside>
  );
}
