import { useMutation } from '@tanstack/react-query';

import { useCallback, useRef } from 'react';

import { Button } from '@/components/ui/button';

import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { FieldGroup, FormField } from '../../shared/ui/FormField';
import { FormStatus } from '../../shared/ui/FormStatus';
import { createTask } from './api';

export function TaskForm({ projectId, disabled = false }: { projectId: number; disabled?: boolean }) {
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
  useSubmitShortcut(submitShortcut, !disabled);

  return (
    <form ref={formRef} className="stacked-form" aria-label="Create task" onSubmit={onSubmit}>
      <FieldGroup>
        <FormField id="task-title" name="title" label="Task title" required disabled={disabled || mutation.isPending} />
        <FormField id="task-assignee" name="assigneeId" label="Assignee ID" type="number" disabled={disabled || mutation.isPending} />
        <FormField id="task-deadline" name="deadlineAt" label="Deadline" type="datetime-local" disabled={disabled || mutation.isPending} />
        <label className="grid gap-1.5 text-sm font-bold text-muted-foreground">
          Priority
          <select name="priority" defaultValue="normal" disabled={disabled || mutation.isPending}>
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
          </select>
        </label>
      </FieldGroup>
      <Button type="submit" disabled={disabled || mutation.isPending}>
        {mutation.isPending ? 'Adding task' : 'Add task'}
      </Button>
      <KeyboardHint>Ctrl+Enter saves</KeyboardHint>
      {disabled ? <p className="text-sm text-muted-foreground">Archived projects are read-only until reopened.</p> : null}
      <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Task created' : undefined} />
    </form>
  );
}
