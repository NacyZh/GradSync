import { useMutation } from '@tanstack/react-query';

import { useCallback, useRef } from 'react';

import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { FormStatus } from '../../shared/ui/FormStatus';
import { createTask } from './api';

export function TaskForm({ projectId }: { projectId: number }) {
  const formRef = useRef<HTMLFormElement>(null);
  const { notify } = useAppFeedback();
  const mutation = useMutation({
    mutationFn: (payload: { title: string; assignee_id?: number; deadline_at?: string; priority?: string }) => createTask(projectId, payload),
    onSuccess: () => notify('Task created', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({
      title: String(form.get('title')),
      assignee_id: Number(form.get('assigneeId')) || undefined,
      deadline_at: String(form.get('deadlineAt') || '') || undefined,
      priority: String(form.get('priority') || 'normal'),
    });
  }

  const submitShortcut = useCallback(() => {
    formRef.current?.requestSubmit();
  }, []);
  useSubmitShortcut(submitShortcut);

  return (
    <form ref={formRef} className="stacked-form" aria-label="Create task" onSubmit={onSubmit}>
      <label>
        Task title
        <input name="title" required />
      </label>
      <label>
        Assignee ID
        <input name="assigneeId" type="number" />
      </label>
      <label>
        Deadline
        <input name="deadlineAt" type="datetime-local" />
      </label>
      <label>
        Priority
        <select name="priority" defaultValue="normal">
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
      </label>
      <button type="submit">Add task</button>
      <KeyboardHint>Ctrl+Enter saves</KeyboardHint>
      <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Task created' : undefined} />
    </form>
  );
}
