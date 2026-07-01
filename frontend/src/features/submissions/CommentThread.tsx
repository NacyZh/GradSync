import { useMutation } from '@tanstack/react-query';
import { MessageSquareText } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { StatusBadge } from '../../shared/ui/StatusBadge';
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
      {comments.length === 0 ? <DataState state="empty" title="No comments" message="No comments for this target yet." /> : null}
      <ul className="timeline">
        {comments.map((comment) => (
          <li key={comment.id}>
            <div className="min-w-0">
              <strong className="flex items-center gap-2">
                <MessageSquareText className="h-4 w-4 text-primary" aria-hidden="true" />
                {comment.anchor}
              </strong>
              <span className="block text-sm text-muted-foreground">{comment.body}</span>
              <small className="block text-xs text-muted-foreground">
                {comment.target_type} #{comment.target_id}
              </small>
            </div>
            <StatusBadge status={comment.status} />
            <Button variant="outline" size="sm" type="button" onClick={() => mutation.mutate(comment.id)} disabled={comment.status === 'resolved' || mutation.isPending}>
              Resolve
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
