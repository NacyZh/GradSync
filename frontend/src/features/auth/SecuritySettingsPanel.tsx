import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Laptop, MailCheck, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';
import { useState } from 'react';

import { formatUiDate } from '@/shared/i18n/translate';
import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { useI18n } from '../i18n/I18nProvider';
import {
  cancelEmailChange,
  fetchAccountSessions,
  fetchEmailChange,
  requestEmailChange,
  resendEmailChange,
  revokeAccountSession,
  revokeOtherAccountSessions,
  verifyEmailChange,
  type AccountSession,
} from './api';

export function SecuritySettingsPanel() {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const queryClient = useQueryClient();
  const [newEmail, setNewEmail] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [sessionToRevoke, setSessionToRevoke] = useState<AccountSession | null>(null);
  const [confirmOthers, setConfirmOthers] = useState(false);
  const emailQuery = useQuery({ queryKey: ['account-security', 'email-change'], queryFn: fetchEmailChange });
  const sessionsQuery = useQuery({ queryKey: ['account-security', 'sessions'], queryFn: fetchAccountSessions });

  const refreshSecurity = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['account-security', 'email-change'] }),
      queryClient.invalidateQueries({ queryKey: ['account-security', 'sessions'] }),
    ]);
  };
  const emailRequest = useMutation({
    mutationFn: requestEmailChange,
    onSuccess: async () => {
      setCurrentPassword('');
      await refreshSecurity();
      notify(t('emailChangeRequested'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const emailVerify = useMutation({
    mutationFn: verifyEmailChange,
    onSuccess: async (user) => {
      queryClient.setQueryData(['current-user'], user);
      setNewEmail('');
      setVerificationCode('');
      await refreshSecurity();
      notify(t('emailChangeCompleted'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const cancelMutation = useMutation({
    mutationFn: cancelEmailChange,
    onSuccess: async () => {
      await refreshSecurity();
      notify(t('emailChangeCancelled'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const resendMutation = useMutation({
    mutationFn: resendEmailChange,
    onSuccess: async () => {
      await refreshSecurity();
      notify(t('emailChangeResent'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const revokeMutation = useMutation({
    mutationFn: revokeAccountSession,
    onSuccess: async () => {
      setSessionToRevoke(null);
      await refreshSecurity();
      notify(t('sessionRevoked'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const revokeOthersMutation = useMutation({
    mutationFn: revokeOtherAccountSessions,
    onSuccess: async ({ revokedCount }) => {
      setConfirmOthers(false);
      await refreshSecurity();
      notify(t('otherSessionsRevoked').replace('{count}', String(revokedCount)), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const pending = emailQuery.data?.pending ? emailQuery.data : null;
  const sessions = sessionsQuery.data?.results ?? [];
  const sessionStatusLabel = {
    active: t('sessionStatusActive'),
    revoked: t('sessionStatusRevoked'),
    expired: t('sessionStatusExpired'),
  };

  return (
    <section className="panel max-w-3xl" aria-labelledby="security-settings-heading">
      <div className="mb-5">
        <h2 id="security-settings-heading" className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-4 w-4" aria-hidden="true" />
          {t('securitySettings')}
        </h2>
        <p className="text-sm text-muted-foreground">{t('securitySettingsDescription')}</p>
      </div>

      <div className="grid gap-6">
        <div className="grid gap-3 border-b pb-6">
          <h3 className="flex items-center gap-2 text-sm">
            <MailCheck className="h-4 w-4" aria-hidden="true" />
            {t('changeEmail')}
          </h3>
          {pending ? (
            <div className="grid gap-3 rounded-md border bg-muted/30 p-4">
              <p className="text-sm">
                {t('pendingEmailChange')}: <strong>{pending.maskedNewEmail}</strong>
              </p>
              <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                <div>
                  <Label htmlFor="email-change-code">{t('verificationCode')}</Label>
                  <Input
                    id="email-change-code"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={verificationCode}
                    onChange={(event) => setVerificationCode(event.target.value)}
                  />
                </div>
                <Button
                  className="self-end"
                  onClick={() => emailVerify.mutate({
                    requestId: pending.requestId ?? '',
                    code: verificationCode,
                  })}
                  disabled={!verificationCode || emailVerify.isPending}
                >
                  {t('verifyEmail')}
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => resendMutation.mutate()}>
                  <RefreshCw className="h-4 w-4" aria-hidden="true" />
                  {t('resendCode')}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => cancelMutation.mutate()}>
                  {t('cancelEmailChange')}
                </Button>
              </div>
            </div>
          ) : (
            <form
              className="grid gap-3 sm:grid-cols-2"
              onSubmit={(event) => {
                event.preventDefault();
                emailRequest.mutate({ newEmail, currentPassword });
              }}
            >
              <div className="grid gap-1.5">
                <Label htmlFor="new-account-email">{t('newEmail')}</Label>
                <Input
                  id="new-account-email"
                  type="email"
                  autoComplete="email"
                  value={newEmail}
                  onChange={(event) => setNewEmail(event.target.value)}
                  required
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="email-change-password">{t('currentPassword')}</Label>
                <Input
                  id="email-change-password"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                />
              </div>
              <Button className="sm:col-span-2 sm:w-fit" type="submit" disabled={!newEmail || !currentPassword || emailRequest.isPending}>
                {t('requestEmailChange')}
              </Button>
            </form>
          )}
        </div>

        <div className="grid gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="flex items-center gap-2 text-sm">
              <Laptop className="h-4 w-4" aria-hidden="true" />
              {t('activeSessions')}
            </h3>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmOthers(true)}
              disabled={!sessions.some((session) => session.status === 'active' && !session.current)}
            >
              {t('signOutOtherDevices')}
            </Button>
          </div>
          <div className="max-h-80 overflow-y-auto rounded-md border">
            {sessionsQuery.isLoading ? (
              <p className="p-4 text-sm text-muted-foreground">{t('loading')}</p>
            ) : sessions.length ? (
              <ul className="divide-y">
                {sessions.map((session) => (
                  <li key={session.id} className="flex min-w-0 items-start justify-between gap-3 p-4">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold">
                        {session.deviceLabel}
                        {session.current ? ` · ${t('currentSession')}` : ''}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {t('lastActive')} {formatUiDate(session.lastSeenAt, { dateStyle: 'medium', timeStyle: 'short' })}
                        {' · '}{sessionStatusLabel[session.status]}
                      </p>
                    </div>
                    {!session.current && session.status === 'active' ? (
                      <Button
                        size="icon"
                        variant="ghost"
                        title={t('revokeSession')}
                        aria-label={t('revokeSession')}
                        onClick={() => setSessionToRevoke(session)}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="p-4 text-sm text-muted-foreground">{t('noSessions')}</p>
            )}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(sessionToRevoke)}
        title={t('revokeSession')}
        message={t('revokeSessionConfirmation')}
        actionLabel={t('revoke')}
        cancelLabel={t('cancel')}
        onCancel={() => setSessionToRevoke(null)}
        onConfirm={() => sessionToRevoke && revokeMutation.mutate(sessionToRevoke.id)}
      />
      <ConfirmDialog
        open={confirmOthers}
        title={t('signOutOtherDevices')}
        message={t('signOutOtherDevicesConfirmation')}
        actionLabel={t('signOut')}
        cancelLabel={t('cancel')}
        onCancel={() => setConfirmOthers(false)}
        onConfirm={() => revokeOthersMutation.mutate()}
      />
    </section>
  );
}
