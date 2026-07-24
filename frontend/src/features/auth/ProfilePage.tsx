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
import { useI18n } from '../i18n/I18nProvider';
import { useAuth } from './AuthProvider';
import { changePassword, updateProfile } from './api';
import { SecuritySettingsPanel } from './SecuritySettingsPanel';

export function ProfilePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useAppFeedback();
  const { t } = useI18n();
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
      notify(t('profileUpdated'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const passwordMutation = useMutation({
    mutationFn: changePassword,
    onSuccess: () => {
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      notify(t('passwordUpdated'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });

  return (
    <PageShell title={t('profileSettings')} description={t('profileSettingsDescription')}>
      <section className="panel max-w-3xl">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-base">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              {t('accountIdentity')}
            </h2>
            <p className="text-sm text-muted-foreground">{t('accountIdentityDescription')}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {user ? <StatusBadge status={user.status} /> : null}
            {user?.active_role ? <StatusBadge status={user.active_role} /> : null}
          </div>
        </div>
        <dl className="grid gap-4 text-sm sm:grid-cols-2">
          <div><dt className="font-bold text-muted-foreground">{t('email')}</dt><dd className="mt-1 break-all">{user?.email}</dd></div>
          <div><dt className="font-bold text-muted-foreground">{t('accountRole')}</dt><dd className="mt-1 capitalize">{user?.global_role ? t(user.global_role === 'advisor' ? 'advisor' : user.global_role) : ''}</dd></div>
        </dl>
      </section>

      <section className="panel max-w-3xl">
        <div className="mb-5">
          <h2 className="flex items-center gap-2 text-base"><UserRound className="h-4 w-4" aria-hidden="true" />{t('personalInformation')}</h2>
          <p className="text-sm text-muted-foreground">{t('nicknameHelp')}</p>
        </div>
        <form
          aria-label={t('updateProfile')}
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
            <Label htmlFor="profile-name">{t('fullName')}</Label>
            <Input id="profile-name" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="profile-nickname">{t('nickname')}</Label>
            <Input id="profile-nickname" value={nickname} onChange={(event) => setNickname(event.target.value)} />
          </div>
          {user?.global_role === 'student' ? (
            <label className="grid gap-1.5 text-sm font-bold">
              {t('degree')}
              <Select value={degreeType} onValueChange={(value) => setDegreeType(value as 'masters' | 'doctoral')}>
                <SelectTrigger aria-label={t('degreeType')}><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="masters">{t('masters')}</SelectItem>
                  <SelectItem value="doctoral">{t('doctoral')}</SelectItem>
                </SelectContent>
              </Select>
            </label>
          ) : null}
          <Button className="self-end sm:col-span-2 sm:w-fit" type="submit" disabled={profileMutation.isPending || !name.trim() || !nickname.trim()}>
            <Save className="h-4 w-4" aria-hidden="true" />
            {profileMutation.isPending ? t('saving') : t('saveProfile')}
          </Button>
        </form>
      </section>

      <section className="panel max-w-3xl">
        <div className="mb-5">
          <h2 className="flex items-center gap-2 text-base"><KeyRound className="h-4 w-4" aria-hidden="true" />{t('password')}</h2>
          <p className="text-sm text-muted-foreground">{t('passwordPolicy')}</p>
        </div>
        <form
          aria-label={t('changePassword')}
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (newPassword !== confirmPassword) {
              notify(t('newPasswordsDoNotMatch'), 'error');
              return;
            }
            passwordMutation.mutate({ currentPassword, newPassword });
          }}
        >
          <div className="grid gap-1.5 sm:col-span-2">
            <Label htmlFor="current-password">{t('currentPassword')}</Label>
            <Input id="current-password" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="new-password">{t('newPassword')}</Label>
            <Input id="new-password" type="password" autoComplete="new-password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="confirm-new-password">{t('confirmNewPassword')}</Label>
            <Input id="confirm-new-password" type="password" autoComplete="new-password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required />
          </div>
          <Button className="sm:col-span-2 sm:w-fit" type="submit" disabled={passwordMutation.isPending || !currentPassword || !newPassword || !confirmPassword}>
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            {passwordMutation.isPending ? t('updating') : t('updatePassword')}
          </Button>
        </form>
      </section>

      <SecuritySettingsPanel />
    </PageShell>
  );
}
