import { useMutation } from '@tanstack/react-query';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import type { InlineComment } from './api';
import { updateCommentStatus } from './api';

export function CommentThread({ projectId, comments = [] }: { projectId?: number; comments?: InlineComment[] }) {
  const { notify } = useAppFeedback();
  const mutation = useMutation({
    mutationFn: (commentId: number) => updateCommentStatus(projectId ?? 0, commentId, 'resolved'),
    onSuccess: () => notify('Comment resolved', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  return (
    <section aria-label="Comment thread">
      {comments.length === 0 ? <p className="muted">No comments for this target yet.</p> : null}
      <ul className="timeline">
        {comments.map((comment) => (
          <li key={comment.id}>
            <strong>{comment.anchor}</strong>
            <span>{comment.body}</span>
            <small>{comment.status}</small>
            <button className="button compact" type="button" onClick={() => mutation.mutate(comment.id)} disabled={comment.status === 'resolved'}>
              Resolve
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
