import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Save } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { FormStatus } from '../../shared/ui/FormStatus';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { useAuth } from './AuthProvider';
import { updateNickname } from './api';

export function ProfilePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [nickname, setNickname] = useState(user?.nickname || user?.name || '');
  const mutation = useMutation({
    mutationFn: updateNickname,
    onSuccess: (updated) => queryClient.setQueryData(['current-user'], updated),
  });

  return (
    <PageShell title="Profile" description="Manage the internal nickname used by project selectors.">
      <section className="panel max-w-2xl">
        <div className="mb-4 flex flex-wrap gap-2">
          {user ? <StatusBadge status={user.status} /> : null}
          {user?.active_role ? <StatusBadge status={user.active_role} /> : null}
        </div>
        <form
          aria-label="Update nickname"
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate(nickname);
          }}
        >
          <div className="grid gap-1.5">
            <Label htmlFor="profile-nickname">Nickname</Label>
            <Input id="profile-nickname" value={nickname} onChange={(event) => setNickname(event.target.value)} />
          </div>
          <Button type="submit" disabled={mutation.isPending || !nickname.trim()}>
            <Save className="h-4 w-4" aria-hidden="true" />
            Save
          </Button>
          <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Profile updated' : undefined} />
        </form>
      </section>
    </PageShell>
  );
}
