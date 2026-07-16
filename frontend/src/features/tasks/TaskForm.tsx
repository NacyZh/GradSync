import { useMutation } from '@tanstack/react-query';

import { useCallback, useRef } from 'react';

import { Button } from '@/shared/ui/primitives/button';

import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { FieldGroup, FormField } from '../../shared/ui/FormField';
import { FormStatus } from '../../shared/ui/FormStatus';
import { createTask } from './api';

type TaskAssignableMember = {
  id: number;
  user_id?: number;
  userId?: number;
  nickname?: string;
  name?: string;
  email?: string;
  status: 'active' | 'removed';
};

export function TaskForm({
  projectId,
  members = [],
  disabled = false,
}: {
  projectId: number;
  members?: TaskAssignableMember[];
  disabled?: boolean;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const { notify } = useAppFeedback();
  const mutation = useMutation({
    mutationFn: (payload: { title: string; assignee_id?: number; assignee_ids?: number[]; deadline_at?: string; priority?: string }) => createTask(projectId, payload),
    onSuccess: () => notify('Task created', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });
  const activeMembers = members.filter((member) => member.status === 'active' && (member.userId ?? member.user_id));

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const assigneeIds = form
      .getAll('assigneeIds')
      .map((value) => Number(value))
      .filter(Boolean);
    mutation.mutate({
      title: String(form.get('title')),
      assignee_id: assigneeIds[0],
      assignee_ids: assigneeIds,
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
        <label className="grid gap-1.5 text-sm font-bold text-muted-foreground" htmlFor="task-assignees">
          Assignees
          <select
            id="task-assignees"
            name="assigneeIds"
            multiple
            className="min-h-24 rounded-md border border-input bg-background px-3 py-2 text-sm"
            disabled={disabled || mutation.isPending || activeMembers.length === 0}
          >
            {activeMembers.map((member) => {
              const userId = member.userId ?? member.user_id;
              const label = member.nickname || member.name || member.email || `User ${userId}`;
              return (
                <option key={member.id} value={userId}>
                  {label}
                </option>
              );
            })}
          </select>
        </label>
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
