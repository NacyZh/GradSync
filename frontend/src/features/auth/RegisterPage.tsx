import { useMutation } from '@tanstack/react-query';
import { CheckCircle2, MailCheck, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { register, verifyEmail, type RegisterPayload } from './api';

export function RegisterPage() {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<RegisterPayload['requestedRole']>('student');
  const [degreeType, setDegreeType] = useState<'masters' | 'doctoral'>('masters');
  const [status, setStatus] = useState<string | null>(null);
  const { notify } = useAppFeedback();

  const registerMutation = useMutation({
    mutationFn: register,
    onSuccess: (result) => {
      setEmail(result.email);
      setStatus(result.status);
      notify('Verification email sent', 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const verifyMutation = useMutation({
    mutationFn: verifyEmail,
    onSuccess: (user) => {
      setStatus(user.status);
      notify('Email verified', 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });

  function onRegister(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    registerMutation.mutate({
      email: String(form.get('email')),
      password: String(form.get('password')),
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
      <section className="login-container" aria-label="Register">
        <div className="login-card">
          <div className="login-header">
            <div>
              <h1>GradSync</h1>
              <p className="login-subtitle">Create a verified research workspace account.</p>
            </div>
            {status ? <StatusBadge status={status} /> : null}
          </div>

          <form aria-label="Register account" onSubmit={onRegister} className="login-form">
            <div className="login-field">
              <Label htmlFor="register-email">Email</Label>
              <Input id="register-email" name="email" type="email" required disabled={registerMutation.isPending} />
            </div>
            <div className="login-field">
              <Label htmlFor="register-nickname">Nickname</Label>
              <Input id="register-nickname" name="nickname" required disabled={registerMutation.isPending} />
            </div>
            <div className="login-field">
              <Label htmlFor="register-password">Password</Label>
              <Input id="register-password" name="password" type="password" required disabled={registerMutation.isPending} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1.5 text-sm font-bold">
                Role
                <Select value={role} onValueChange={(value) => setRole(value as RegisterPayload['requestedRole'])}>
                  <SelectTrigger aria-label="Requested role"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="student">Student</SelectItem>
                    <SelectItem value="teacher">Teacher</SelectItem>
                    <SelectItem value="administrator">Administrator</SelectItem>
                  </SelectContent>
                </Select>
              </label>
              {role === 'student' ? (
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
            </div>
            <Button type="submit" disabled={registerMutation.isPending}>
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              {registerMutation.isPending ? 'Registering' : 'Register'}
            </Button>
          </form>

          {email ? (
            <form aria-label="Verify email" onSubmit={onVerify} className="login-form border-t pt-4">
              <div className="login-field">
                <Label htmlFor="verification-code">Verification code</Label>
                <Input id="verification-code" name="code" inputMode="numeric" required disabled={verifyMutation.isPending} />
              </div>
              <Button type="submit" variant="outline" disabled={verifyMutation.isPending}>
                <MailCheck className="h-4 w-4" aria-hidden="true" />
                Verify email
              </Button>
              {status === 'active' ? <p className="flex items-center gap-2 text-sm"><CheckCircle2 className="h-4 w-4" /> Account active</p> : null}
            </form>
          ) : null}
          <Link className="text-sm font-semibold text-primary" to="/login">Sign in</Link>
        </div>
      </section>
    </main>
  );
}
