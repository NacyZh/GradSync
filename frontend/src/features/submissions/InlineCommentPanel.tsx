import { useMutation, useQuery } from '@tanstack/react-query';

import { createComment, listComments } from './api';

export function InlineCommentPanel({ projectId, targetType, targetId }: { projectId?: number; targetType?: string; targetId?: number }) {
  const commentsQuery = useQuery({
    queryKey: ['comments', projectId, targetType, targetId],
    queryFn: () => listComments(projectId ?? 0, targetType, targetId),
    enabled: Boolean(projectId),
  });
  const mutation = useMutation({
    mutationFn: (payload: { anchor: string; body: string }) =>
      createComment(projectId ?? 0, { target_type: targetType ?? 'draft_version', target_id: targetId ?? 0, ...payload }),
    onSuccess: () => commentsQuery.refetch(),
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({ anchor: String(form.get('anchor') ?? 'general'), body: String(form.get('body')) });
  }

  return (
    <aside aria-label="Inline comments">
      <ul>
        {commentsQuery.data?.results.map((comment) => (
          <li key={comment.id}>
            {comment.anchor}: {comment.body} ({comment.status})
          </li>
        ))}
      </ul>
      <form onSubmit={onSubmit}>
        <label>
          Anchor
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
