import { useMutation } from '@tanstack/react-query';

import type { InlineComment } from './api';
import { updateCommentStatus } from './api';

export function CommentThread({ projectId, comments = [] }: { projectId?: number; comments?: InlineComment[] }) {
  const mutation = useMutation({ mutationFn: (commentId: number) => updateCommentStatus(projectId ?? 0, commentId, 'resolved') });

  return (
    <section aria-label="Comment thread">
      <ul>
        {comments.map((comment) => (
          <li key={comment.id}>
            {comment.body}
            <button type="button" onClick={() => mutation.mutate(comment.id)}>
              Resolve
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
