import { useMutation } from '@tanstack/react-query';

import type { ProjectMembership } from './api';
import { addProjectMember } from './api';
import { FormStatus } from '../../shared/ui/FormStatus';

export function ProjectMembersPanel({ projectId, members = [] }: { projectId: number; members?: ProjectMembership[] }) {
  const mutation = useMutation({ mutationFn: (payload: { user_id: number; role: ProjectMembership['role'] }) => addProjectMember(projectId, payload) });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({ user_id: Number(form.get('userId')), role: String(form.get('role')) as ProjectMembership['role'] });
  }

  return (
    <section aria-labelledby="project-members-heading">
      <h2 id="project-members-heading">Project members</h2>
      {members.length === 0 ? <p>No members loaded yet.</p> : null}
      <ul>
        {members.map((member) => (
          <li key={member.id}>
            User {member.user_id}: {member.role} ({member.status})
          </li>
        ))}
      </ul>
      <form aria-label="Add project member" onSubmit={onSubmit}>
        <label>
          User ID
          <input name="userId" type="number" required />
        </label>
        <label>
          Role
          <select name="role" defaultValue="student">
            <option value="student">Student</option>
            <option value="reviewer">Reviewer</option>
            <option value="observer">Observer</option>
            <option value="advisor">Advisor</option>
          </select>
        </label>
        <button type="submit">Add member</button>
        <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Member added' : undefined} />
      </form>
    </section>
  );
}
