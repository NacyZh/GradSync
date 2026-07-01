import { useMutation } from '@tanstack/react-query';
import { UserPlus, UsersRound } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FormField } from '../../shared/ui/FormField';
import type { ProjectMembership } from './api';
import { addProjectMember } from './api';
import { FormStatus } from '../../shared/ui/FormStatus';
import { StatusBadge } from '../../shared/ui/StatusBadge';

export function ProjectMembersPanel({ projectId, members = [], disabled = false }: { projectId: number; members?: ProjectMembership[]; disabled?: boolean }) {
  const mutation = useMutation({ mutationFn: (payload: { user_id: number; role: ProjectMembership['role'] }) => addProjectMember(projectId, payload) });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({ user_id: Number(form.get('userId')), role: String(form.get('role')) as ProjectMembership['role'] });
  }

  return (
    <section aria-labelledby="project-members-heading" className="grid gap-4">
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
            <span>
              <strong>User {member.user_id}</strong>
              <span className="ml-2 text-muted-foreground">{member.role}</span>
            </span>
            <StatusBadge status={member.status} />
          </li>
        ))}
      </ul>
      <Card className="shadow-none">
        <CardHeader className="p-4">
          <CardTitle className="flex items-center gap-2 text-base">
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            Add member
          </CardTitle>
          <CardDescription>Members inherit project-scoped visibility.</CardDescription>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <form aria-label="Add project member" onSubmit={onSubmit} className="grid gap-3">
            <FormField id="member-user-id" name="userId" label="User ID" type="number" required disabled={disabled || mutation.isPending} />
            <label className="grid gap-1.5 text-sm font-bold text-muted-foreground">
              Role
              <select name="role" defaultValue="student" disabled={disabled || mutation.isPending}>
                <option value="student">Student</option>
                <option value="reviewer">Reviewer</option>
                <option value="observer">Observer</option>
                <option value="advisor">Advisor</option>
              </select>
            </label>
            <Button type="submit" variant="outline" disabled={disabled || mutation.isPending}>
              Add member
            </Button>
            {disabled ? <p className="text-sm text-muted-foreground">Archived projects are read-only until reopened.</p> : null}
            <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Member added' : undefined} />
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
