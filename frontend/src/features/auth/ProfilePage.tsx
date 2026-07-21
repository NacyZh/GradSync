import { useMutation, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Save, ShieldCheck, UserRound } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { useAuth } from './AuthProvider';
import { changePassword, updateProfile } from './api';

export function ProfilePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useAppFeedback();
  const [name, setName] = useState(user?.name || '');
  const [nickname, setNickname] = useState(user?.nickname || user?.name || '');
  const [degreeType, setDegreeType] = useState<'masters' | 'doctoral'>(user?.degreeType || 'masters');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  useEffect(() => {
    if (!user) return;
    setName(user.name);
    setNickname(user.nickname || user.name);
    setDegreeType(user.degreeType || 'masters');
  }, [user]);

  const profileMutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: (updated) => {
      queryClient.setQueryData(['current-user'], updated);
      notify('Profile updated', 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const passwordMutation = useMutation({
    mutationFn: changePassword,
    onSuccess: () => {
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      notify('Password updated', 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });

  return (
    <PageShell title="Profile settings" description="Manage your identity, research role, and account security.">
      <section className="panel max-w-3xl">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-base">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              Account identity
            </h2>
            <p className="text-sm text-muted-foreground">Your email and approved role are managed as account credentials.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {user ? <StatusBadge status={user.status} /> : null}
            {user?.active_role ? <StatusBadge status={user.active_role} /> : null}
          </div>
        </div>
        <dl className="grid gap-4 text-sm sm:grid-cols-2">
          <div><dt className="font-bold text-muted-foreground">Email</dt><dd className="mt-1 break-all">{user?.email}</dd></div>
          <div><dt className="font-bold text-muted-foreground">Account role</dt><dd className="mt-1 capitalize">{user?.global_role === 'advisor' ? 'Teacher' : user?.global_role}</dd></div>
        </dl>
      </section>

      <section className="panel max-w-3xl">
        <div className="mb-5">
          <h2 className="flex items-center gap-2 text-base"><UserRound className="h-4 w-4" aria-hidden="true" />Personal information</h2>
          <p className="text-sm text-muted-foreground">The workspace nickname identifies you in member and task selectors.</p>
        </div>
        <form
          aria-label="Update profile"
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            profileMutation.mutate({
              name: name.trim(),
              nickname: nickname.trim(),
              degreeType: user?.global_role === 'student' ? degreeType : undefined,
            });
          }}
        >
          <div className="grid gap-1.5">
            <Label htmlFor="profile-name">Full name</Label>
            <Input id="profile-name" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="profile-nickname">Nickname</Label>
            <Input id="profile-nickname" value={nickname} onChange={(event) => setNickname(event.target.value)} />
          </div>
          {user?.global_role === 'student' ? (
            <label className="grid gap-1.5 text-sm font-bold">
              Degree
              <Select value={degreeType} onValueChange={(value) => setDegreeType(value as 'masters' | 'doctoral')}>
                <SelectTrigger aria-label="Degree type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="masters">Masters</SelectItem>
                  <SelectItem value="doctoral">Doctoral</SelectItem>
                </SelectContent>
              </Select>
            </label>
          ) : null}
          <Button className="self-end sm:col-span-2 sm:w-fit" type="submit" disabled={profileMutation.isPending || !name.trim() || !nickname.trim()}>
            <Save className="h-4 w-4" aria-hidden="true" />
            {profileMutation.isPending ? 'Saving' : 'Save profile'}
          </Button>
        </form>
      </section>

      <section className="panel max-w-3xl">
        <div className="mb-5">
          <h2 className="flex items-center gap-2 text-base"><KeyRound className="h-4 w-4" aria-hidden="true" />Password</h2>
          <p className="text-sm text-muted-foreground">Use at least eight characters with upper and lower case letters, a number, and a symbol.</p>
        </div>
        <form
          aria-label="Change password"
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (newPassword !== confirmPassword) {
              notify('New passwords do not match', 'error');
              return;
            }
            passwordMutation.mutate({ currentPassword, newPassword });
          }}
        >
          <div className="grid gap-1.5 sm:col-span-2">
            <Label htmlFor="current-password">Current password</Label>
            <Input id="current-password" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="new-password">New password</Label>
            <Input id="new-password" type="password" autoComplete="new-password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="confirm-new-password">Confirm new password</Label>
            <Input id="confirm-new-password" type="password" autoComplete="new-password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required />
          </div>
          <Button className="sm:col-span-2 sm:w-fit" type="submit" disabled={passwordMutation.isPending || !currentPassword || !newPassword || !confirmPassword}>
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            {passwordMutation.isPending ? 'Updating' : 'Update password'}
          </Button>
        </form>
      </section>
    </PageShell>
  );
}
