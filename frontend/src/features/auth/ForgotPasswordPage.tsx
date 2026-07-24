import { useMutation } from '@tanstack/react-query';
import { ArrowLeft, Mail } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { LanguageSwitcher } from '../i18n/LanguageSwitcher';
import { useI18n } from '../i18n/I18nProvider';
import { requestPasswordRecovery } from './api';

export function ForgotPasswordPage() {
  const { t } = useI18n();
  const [email, setEmail] = useState('');
  const [acknowledgement, setAcknowledgement] = useState('');
  const mutation = useMutation({
    mutationFn: requestPasswordRecovery,
    onSuccess: (result) => setAcknowledgement(result.message),
  });

  return (
    <main className="login-screen">
      <section className="login-container" aria-label={t('passwordRecovery')}>
        <div className="login-card">
          <div className="login-header">
            <div>
              <h1>GradSync</h1>
              <p className="login-subtitle">{t('passwordRecoveryDescription')}</p>
            </div>
            <LanguageSwitcher />
          </div>
          {acknowledgement ? (
            <div className="grid gap-4" role="status">
              <div className="rounded-md border bg-muted/40 p-4 text-sm">
                {t('recoveryGenericAcknowledgement')}
              </div>
              <Button asChild variant="outline">
                <Link to="/login">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  {t('backToSignIn')}
                </Link>
              </Button>
            </div>
          ) : (
            <form
              className="login-form"
              onSubmit={(event) => {
                event.preventDefault();
                mutation.mutate({ email, returnTo: '/reset-password' });
              }}
            >
              <div className="login-field">
                <Label htmlFor="recovery-email">{t('email')}</Label>
                <Input
                  id="recovery-email"
                  className="login-input"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>
              <Button type="submit" disabled={!email.trim() || mutation.isPending}>
                <Mail className="h-4 w-4" aria-hidden="true" />
                {mutation.isPending ? t('sendingRecoveryInstructions') : t('sendRecoveryInstructions')}
              </Button>
              <Button asChild variant="link">
                <Link to="/login">{t('backToSignIn')}</Link>
              </Button>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}

