import { useMutation } from '@tanstack/react-query';

import { useCallback, useMemo, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';

import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { FieldGroup, FormField, TextareaField } from '../../shared/ui/FormField';
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
    mutationFn: (payload: { title: string; description?: string; assignee_id?: number; assignee_ids?: number[]; deadline_at?: string; priority?: string }) => createTask(projectId, payload),
    onSuccess: () => notify('Task created', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });
  const [assigneeQuery, setAssigneeQuery] = useState('');
  const [selectedAssigneeIds, setSelectedAssigneeIds] = useState<number[]>([]);
  const activeMembers = useMemo(
    () => members.filter((member) => member.status === 'active' && (member.userId ?? member.user_id)),
    [members],
  );
  const selectedAssignees = selectedAssigneeIds
    .map((userId) => activeMembers.find((member) => (member.userId ?? member.user_id) === userId))
    .filter((member): member is TaskAssignableMember => Boolean(member));
  const assigneeOptions = activeMembers.filter((member) => {
    const userId = member.userId ?? member.user_id;
    if (!userId || selectedAssigneeIds.includes(userId)) return false;
    const label = memberLabel(member).toLowerCase();
    return !assigneeQuery.trim() || label.includes(assigneeQuery.toLowerCase());
  });
  const showAssigneeOptions = !disabled && assigneeOptions.length > 0 && assigneeQuery.trim().length > 0;

  function addAssignee(member: TaskAssignableMember) {
    const userId = member.userId ?? member.user_id;
    if (!userId || selectedAssigneeIds.includes(userId)) return;
    setSelectedAssigneeIds((current) => [...current, userId]);
    setAssigneeQuery('');
  }

  function removeAssignee(userId: number) {
    setSelectedAssigneeIds((current) => current.filter((selectedId) => selectedId !== userId));
  }

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({
      title: String(form.get('title')),
      description: String(form.get('description') ?? ''),
      assignee_id: selectedAssigneeIds[0],
      assignee_ids: selectedAssigneeIds,
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
        <TextareaField id="task-description" name="description" label="Task description" placeholder="Scope, expected output, acceptance criteria, or useful context." disabled={disabled || mutation.isPending} />
        <div className="grid gap-2">
          <label className="grid gap-1.5 text-sm font-bold text-muted-foreground" htmlFor="task-assignees">
            Assignees
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <Input
                id="task-assignees"
                className="pl-9"
                value={assigneeQuery}
                onChange={(event) => setAssigneeQuery(event.target.value)}
                disabled={disabled || mutation.isPending || activeMembers.length === 0}
                placeholder="Search project members"
                autoComplete="off"
                aria-controls="task-assignee-options"
                aria-expanded={showAssigneeOptions}
              />
            </span>
          </label>
          {showAssigneeOptions ? (
            <ul id="task-assignee-options" className="grid max-h-48 gap-1 overflow-auto rounded-md border bg-popover p-1 shadow-md" role="listbox" aria-label="Assignee options">
              {assigneeOptions.map((member) => {
                return (
                  <li key={member.id}>
                    <button type="button" className="w-full rounded-sm px-2 py-2 text-left text-sm hover:bg-muted" onClick={() => addAssignee(member)} role="option" aria-selected={false}>
                      {memberLabel(member)}
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
          {selectedAssignees.length ? (
            <ul className="flex flex-wrap gap-2" aria-label="Selected assignees">
              {selectedAssignees.map((member) => {
                const userId = member.userId ?? member.user_id;
                return (
                  <li key={userId} className="inline-flex max-w-full items-center gap-2 rounded-md border px-2 py-1 text-sm">
                    <span className="truncate">{memberLabel(member)}</span>
                    <input type="hidden" name="assigneeIds" value={userId} />
                    <Button type="button" variant="ghost" size="icon" aria-label={`Remove ${memberLabel(member)}`} onClick={() => userId && removeAssignee(userId)} disabled={disabled || mutation.isPending}>
                      <X className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
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
    </form>
  );
}

function memberLabel(member: TaskAssignableMember) {
  const userId = member.userId ?? member.user_id;
  return member.nickname || member.name || member.email || `User ${userId}`;
}
