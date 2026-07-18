import { useMutation } from '@tanstack/react-query';

import { Label } from '@/shared/ui/primitives/label';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { updateTask } from './api';

export function TaskStatusControl({ projectId, taskId, status, disabled = false }: { projectId: number; taskId: number; status: string; disabled?: boolean }) {
  const { notify } = useAppFeedback();
  const mutation = useMutation({
    mutationFn: (nextStatus: string) => updateTask(projectId, taskId, { status: nextStatus }),
    onSuccess: () => notify('Task status updated', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  return (
    <div id={`task-${taskId}-status`} className="grid gap-2">
      <Label htmlFor={`task-${taskId}-status-select`}>Status</Label>
      <select
        id={`task-${taskId}-status-select`}
        defaultValue={status}
        onChange={(event) => mutation.mutate(event.target.value)}
        aria-label="Task status"
        disabled={disabled || mutation.isPending}
      >
        <option value="not_started">Not started</option>
        <option value="in_progress">In progress</option>
        <option value="blocked">Blocked</option>
        <option value="submitted">Submitted</option>
        <option value="completed">Completed</option>
        <option value="cancelled">Cancelled</option>
      </select>
      {disabled ? <span className="text-sm text-muted-foreground">Archived projects are read-only until reopened.</span> : null}
    </div>
  );
}
