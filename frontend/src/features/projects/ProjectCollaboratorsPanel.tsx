import { useMutation, useQueryClient } from '@tanstack/react-query';
import { UserPlus, UsersRound } from 'lucide-react';
import { useState } from 'react';

import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { Button } from '@/shared/ui/primitives/button';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';

import {
  addProjectCollaborator,
  type CollaboratorRole,
  type ProjectMembership,
  type TeacherOption,
} from './api';
import { TeacherSelector } from './TeacherSelector';
import { useI18n } from '@/shared/i18n/I18nProvider';

export function ProjectCollaboratorsPanel({
  projectId,
  members,
  canManage,
  disabled,
}: {
  projectId: number;
  members: ProjectMembership[];
  canManage: boolean;
  disabled?: boolean;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { notify } = useAppFeedback();
  const [teacher, setTeacher] = useState<TeacherOption | null>(null);
  const [role, setRole] = useState<CollaboratorRole>('co_advisor');
  const mutation = useMutation({
    mutationFn: () => addProjectCollaborator(projectId, { userId: teacher!.id, role }),
    onSuccess: async () => {
      setTeacher(null);
      notify('Collaborator assigned', 'success');
      await queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const collaborators = members.filter((member) => member.role !== 'student');

  return (
    <section className="panel grid min-h-0 gap-4" aria-label={t('projectCollaborators')}>
      <div>
        <h2 className="flex items-center gap-2">
          <UsersRound className="h-4 w-4" aria-hidden="true" />
          {t('collaborators')}
        </h2>
        <p className="text-sm text-muted-foreground">{t('collaboratorDescription')}</p>
      </div>
      <ul className="max-h-72 divide-y overflow-y-auto rounded-md border">
        {collaborators.map((member) => (
          <li key={member.id} className="grid min-w-0 gap-1 p-3 text-sm">
            <strong className="truncate">{member.nickname || member.name || member.email}</strong>
            <span className="text-muted-foreground">{member.role.replace('_', ' ')}</span>
          </li>
        ))}
      </ul>
      {canManage ? (
        <form
          className="grid gap-3 border-t pt-4 sm:grid-cols-[minmax(0,1fr)_10rem_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            if (teacher) mutation.mutate();
          }}
        >
          <TeacherSelector projectId={projectId} value={teacher} onSelect={setTeacher} disabled={disabled} />
          <div className="grid gap-1.5">
            <Label>Role</Label>
            <Select value={role} onValueChange={(value) => setRole(value as CollaboratorRole)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="co_advisor">{t('coAdvisor')}</SelectItem>
                <SelectItem value="reviewer">{t('reviewer')}</SelectItem>
                <SelectItem value="observer">{t('observer')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button className="self-end" type="submit" disabled={!teacher || disabled || mutation.isPending}>
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            {t('add')}
          </Button>
        </form>
      ) : null}
    </section>
  );
}
