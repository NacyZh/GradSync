import { useMutation } from '@tanstack/react-query';

import { updateTask } from './api';

export function TaskStatusControl({ projectId, taskId, status }: { projectId: number; taskId: number; status: string }) {
  const mutation = useMutation({ mutationFn: (nextStatus: string) => updateTask(projectId, taskId, { status: nextStatus }) });

  return (
    <label>
      Status
      <select defaultValue={status} onChange={(event) => mutation.mutate(event.target.value)} aria-label="Task status">
        <option value="not_started">Not started</option>
        <option value="in_progress">In progress</option>
        <option value="blocked">Blocked</option>
        <option value="submitted">Submitted</option>
        <option value="completed">Completed</option>
        <option value="cancelled">Cancelled</option>
      </select>
      {mutation.isSuccess ? <span role="status">Task status updated</span> : null}
      {mutation.error ? <span role="alert">{mutation.error.message}</span> : null}
    </label>
  );
}
