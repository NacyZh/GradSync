import { useMutation } from '@tanstack/react-query';

import { FormStatus } from '../../shared/ui/FormStatus';
import { createTask } from './api';

export function TaskForm({ projectId }: { projectId: number }) {
  const mutation = useMutation({ mutationFn: (payload: { title: string; assignee_id?: number }) => createTask(projectId, payload) });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({ title: String(form.get('title')), assignee_id: Number(form.get('assigneeId')) || undefined });
  }

  return (
    <form aria-label="Create task" onSubmit={onSubmit}>
      <label>
        Task title
        <input name="title" required />
      </label>
      <label>
        Assignee ID
        <input name="assigneeId" type="number" />
      </label>
      <button type="submit">Add task</button>
      <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Task created' : undefined} />
    </form>
  );
}
