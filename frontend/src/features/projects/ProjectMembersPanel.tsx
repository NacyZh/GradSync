import { useMutation, useQueryClient } from '@tanstack/react-query';
import { UserMinus, UserPlus, UsersRound } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import type { ProjectMembership } from './api';
import { addProjectMember, removeProjectMember } from './api';
import { FormStatus } from '../../shared/ui/FormStatus';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { StudentSelector } from './StudentSelector';

export function ProjectMembersPanel({ projectId, members = [], disabled = false }: { projectId: number; members?: ProjectMembership[]; disabled?: boolean }) {
  const queryClient = useQueryClient();
  const { confirm } = useAppFeedback();
  const [successMessage, setSuccessMessage] = useState<string>();
  const addMutation = useMutation({
    mutationFn: (payload: { studentId: number }) => addProjectMember(projectId, payload),
    onMutate: () => setSuccessMessage(undefined),
    onSuccess: () => {
      setSuccessMessage('Member added');
      return queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
  const removeMutation = useMutation({
    mutationFn: (membershipId: number) => removeProjectMember(projectId, membershipId),
    onMutate: () => setSuccessMessage(undefined),
    onSuccess: () => {
      setSuccessMessage('Member removed');
      return queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });

  async function onRemove(member: ProjectMembership) {
    const memberName = member.nickname || member.name || member.email || `User ${member.userId ?? member.user_id}`;
    const ok = await confirm({
      title: 'Remove student?',
      message: `${memberName} will immediately lose project-scoped access. Group-wide shared assets remain visible.`,
      actionLabel: 'Remove student',
    });
    if (ok) {
      removeMutation.mutate(member.id);
    }
  }

  return (
    <section aria-labelledby="project-members-heading" aria-label="Project members" className="grid gap-4">
      <div>
        <h2 id="project-members-heading" className="flex items-center gap-2 text-base font-extrabold">
          <UsersRound className="h-4 w-4" aria-hidden="true" />
          Project members
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">{members.length} loaded members</p>
      </div>
      {members.length === 0 ? <p className="text-sm text-muted-foreground">No members loaded yet.</p> : null}
      <ul className="grid gap-2">
        {members.map((member) => (
          <li key={member.id} className="flex items-center justify-between gap-3 rounded-md border p-3 text-sm">
            <span className="min-w-0">
              <strong>{member.nickname || member.name || `User ${member.userId ?? member.user_id}`}</strong>
              {member.email ? <span className="ml-2 text-muted-foreground">{member.email}</span> : null}
              <span className="ml-2 text-muted-foreground">{member.role}</span>
            </span>
            <span className="flex shrink-0 flex-wrap items-center justify-end gap-2">
              <StatusBadge status={member.status} />
              {member.role === 'student' && member.status === 'active' ? (
                <Button type="button" variant="outline" size="sm" onClick={() => onRemove(member)} disabled={disabled || removeMutation.isPending}>
                  <UserMinus className="h-4 w-4" aria-hidden="true" />
                  Remove {member.nickname || member.name || `User ${member.userId ?? member.user_id}`}
                </Button>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
      <form aria-label="Add project member" className="grid gap-3 rounded-md border p-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-extrabold">
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            Add student
          </h3>
          <p className="text-sm text-muted-foreground">Search by nickname or email; duplicate nicknames are disambiguated by email and degree.</p>
        </div>
        <StudentSelector onSelect={(student) => addMutation.mutate({ studentId: student.id })} disabled={disabled || addMutation.isPending} />
        {disabled ? <p className="text-sm text-muted-foreground">Archived projects are read-only until reopened.</p> : null}
        <FormStatus
          error={addMutation.error?.message ?? removeMutation.error?.message}
          success={successMessage}
        />
      </form>
    </section>
  );
}
