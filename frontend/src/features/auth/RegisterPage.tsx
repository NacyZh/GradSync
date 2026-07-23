import { useMutation } from '@tanstack/react-query';
import { CheckCircle2, MailCheck, RotateCw, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { LanguageSwitcher } from '../i18n/LanguageSwitcher';
import { useI18n } from '../i18n/I18nProvider';
import { register, resendVerification, verifyEmail, type RegisterPayload } from './api';

export function RegisterPage() {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<RegisterPayload['requestedRole']>('student');
  const [degreeType, setDegreeType] = useState<'masters' | 'doctoral'>('masters');
  const [status, setStatus] = useState<string | null>(null);
  const [passwordMismatch, setPasswordMismatch] = useState(false);
  const { notify } = useAppFeedback();
  const { t } = useI18n();

  const registerMutation = useMutation({
    mutationFn: register,
    onSuccess: (result) => {
      setEmail(result.email);
      setStatus(result.status);
      notify(
        result.status === 'pending_role_activation'
          ? t('accessRequestSubmitted')
          : t('verificationEmailSent'),
        'success',
      );
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const verifyMutation = useMutation({
    mutationFn: verifyEmail,
    onSuccess: (user) => {
      setStatus(user.status);
      notify(t('emailVerified'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const resendMutation = useMutation({
    mutationFn: resendVerification,
    onSuccess: (result) => notify(result.message, 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  function onRegister(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get('password'));
    if (password !== String(form.get('confirmPassword'))) {
      setPasswordMismatch(true);
      notify(t('passwordsDoNotMatch'), 'error');
      return;
    }
    setPasswordMismatch(false);
    registerMutation.mutate({
      email: String(form.get('email')),
      password,
      name: String(form.get('name')),
      nickname: String(form.get('nickname')),
      requestedRole: role,
      degreeType: role === 'student' ? degreeType : undefined,
    });
  }

  function onVerify(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    verifyMutation.mutate({ email, code: String(form.get('code')) });
  }

  return (
    <main className="login-screen">
      <section className="login-container" aria-label={t('register')}>
        <div className="login-card">
          <div className="login-header">
            <div>
              <h1>GradSync</h1>
              <p className="login-subtitle">{t('createWorkspaceAccount')}</p>
            </div>
            <div className="flex items-center gap-2"><LanguageSwitcher />{status ? <StatusBadge status={status} /> : null}</div>
          </div>

          <form aria-label={t('registerAccount')} onSubmit={onRegister} className="login-form">
            <div className="login-field">
              <Label htmlFor="register-email">{t('email')}</Label>
              <Input id="register-email" name="email" type="email" required disabled={registerMutation.isPending} />
            </div>
            <div className="login-field">
              <Label htmlFor="register-name">{t('fullName')}</Label>
              <Input id="register-name" name="name" autoComplete="name" required disabled={registerMutation.isPending} />
            </div>
            <div className="login-field">
              <Label htmlFor="register-nickname">{t('workspaceNickname')}</Label>
              <Input id="register-nickname" name="nickname" required disabled={registerMutation.isPending} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="login-field">
                <Label htmlFor="register-password">{t('password')}</Label>
                <Input id="register-password" name="password" type="password" autoComplete="new-password" minLength={8} required disabled={registerMutation.isPending} />
              </div>
              <div className="login-field">
                <Label htmlFor="register-password-confirm">{t('confirmPassword')}</Label>
                <Input id="register-password-confirm" name="confirmPassword" type="password" autoComplete="new-password" minLength={8} aria-invalid={passwordMismatch} required disabled={registerMutation.isPending} />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1.5 text-sm font-bold">
                {t('role')}
                <Select value={role} onValueChange={(value) => setRole(value as RegisterPayload['requestedRole'])}>
                  <SelectTrigger aria-label={t('requestedRole')}><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="student">{t('student')}</SelectItem>
                    <SelectItem value="teacher">{t('teacher')}</SelectItem>
                  </SelectContent>
                </Select>
              </label>
              {role === 'student' ? (
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
            </div>
            <Button type="submit" disabled={registerMutation.isPending}>
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              {registerMutation.isPending ? t('registering') : t('register')}
            </Button>
          </form>

          {email && status === 'pending_email_verification' ? (
            <form aria-label={t('verifyEmail')} onSubmit={onVerify} className="login-form border-t pt-4">
              <div className="login-field">
                <Label htmlFor="verification-code">{t('verificationCode')}</Label>
                <Input id="verification-code" name="code" inputMode="numeric" required disabled={verifyMutation.isPending} />
              </div>
              <Button type="submit" variant="outline" disabled={verifyMutation.isPending}>
                <MailCheck className="h-4 w-4" aria-hidden="true" />
                {t('verifyEmail')}
              </Button>
              <Button type="button" variant="ghost" disabled={resendMutation.isPending} onClick={() => resendMutation.mutate(email)}>
                <RotateCw className="h-4 w-4" aria-hidden="true" />
                {t('resendCode')}
              </Button>
            </form>
          ) : null}
          {status === 'active' ? <p className="flex items-center gap-2 text-sm"><CheckCircle2 className="h-4 w-4" /> {t('accountActive')}</p> : null}
          {status === 'pending_role_activation' ? <p className="text-sm text-muted-foreground">{t('teacherApprovalPending')}</p> : null}
          <Link className="text-sm font-semibold text-primary" to="/login">{t('signIn')}</Link>
        </div>
      </section>
    </main>
  );
}
