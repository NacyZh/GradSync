import { useMutation } from '@tanstack/react-query';
import { KeyRound } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { LanguageSwitcher } from '../i18n/LanguageSwitcher';
import { useI18n } from '../i18n/I18nProvider';
import { confirmPasswordRecovery } from './api';

export function ResetPasswordPage() {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const requestId = params.get('requestId') ?? '';
  const token = params.get('token') ?? '';
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const mutation = useMutation({
    mutationFn: confirmPasswordRecovery,
    onSuccess: () => {
      notify(t('passwordRecoveryCompleted'), 'success');
      navigate('/login', { replace: true });
    },
    onError: () => notify(t('recoveryLinkInvalid'), 'error'),
  });
  const validLink = Boolean(requestId && token);

  return (
    <main className="login-screen">
      <section className="login-container" aria-label={t('resetPassword')}>
        <div className="login-card">
          <div className="login-header">
            <div>
              <h1>GradSync</h1>
              <p className="login-subtitle">{t('chooseNewPassword')}</p>
            </div>
            <LanguageSwitcher />
          </div>
          {!validLink ? (
            <div className="grid gap-4">
              <p className="rounded-md border bg-muted/40 p-4 text-sm">{t('recoveryLinkInvalid')}</p>
              <Button asChild>
                <Link to="/forgot-password">{t('requestNewRecoveryLink')}</Link>
              </Button>
            </div>
          ) : (
            <form
              className="login-form"
              onSubmit={(event) => {
                event.preventDefault();
                if (newPassword !== confirmation) {
                  notify(t('newPasswordsDoNotMatch'), 'error');
                  return;
                }
                mutation.mutate({ requestId, token, newPassword });
              }}
            >
              <div className="login-field">
                <Label htmlFor="recovery-new-password">{t('newPassword')}</Label>
                <Input
                  id="recovery-new-password"
                  className="login-input"
                  type="password"
                  autoComplete="new-password"
                  minLength={10}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  required
                />
              </div>
              <div className="login-field">
                <Label htmlFor="recovery-confirm-password">{t('confirmNewPassword')}</Label>
                <Input
                  id="recovery-confirm-password"
                  className="login-input"
                  type="password"
                  autoComplete="new-password"
                  minLength={10}
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                  required
                />
              </div>
              <Button
                type="submit"
                disabled={!newPassword || !confirmation || mutation.isPending}
              >
                <KeyRound className="h-4 w-4" aria-hidden="true" />
                {mutation.isPending ? t('updating') : t('resetPassword')}
              </Button>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}

