import { useEffect, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { Link, Navigate } from 'react-router-dom';

import { useAuth } from './AuthProvider';
import { useI18n } from '../i18n/I18nProvider';
import { LanguageSwitcher } from '../i18n/LanguageSwitcher';
import { AsyncState } from '../../shared/ui/AsyncState';
import { useAppFeedback } from '../../shared/ui/AppFeedback';

export function LoginPage() {
  return <LoginContent />;
}

function LoginContent() {
  const { user, isLoading, login, isLoggingIn, loginError } = useAuth();
  const { t } = useI18n();
  const { notify } = useAppFeedback();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (loginError) {
      notify(loginError, 'error');
    }
  }, [loginError, notify]);

  if (isLoading) {
    return <AsyncState state="loading" message="Loading account" />;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim() || !password) return;
    login(email, password).catch(() => {
      // Error is handled via loginError from useAuth context.
    });
  }

  return (
    <main className="login-screen">
      <section className="login-container" aria-label="Authentication">
        <div className="login-card">
          <div className="login-header">
            <div>
              <h1>GradSync</h1>
              <p className="login-subtitle">{t('loginSubtitle')}</p>
            </div>
            <LanguageSwitcher />
          </div>

          <form aria-label={t('signIn')} onSubmit={onSubmit} className="login-form">
            <div className="login-field">
              <label htmlFor="login-email">{t('email')}</label>
              <input
                id="login-email"
                className="login-input"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoggingIn}
              />
            </div>
            <div className="login-field">
              <label htmlFor="login-password">{t('password')}</label>
              <span className="login-password-row">
                <input
                  id="login-password"
                  className="login-input"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoggingIn}
                />
                <button
                  className="login-password-toggle"
                  type="button"
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((current) => !current)}
                  disabled={isLoggingIn}
                >
                  <span className="sr-only">{showPassword ? t('hidePassword') : t('showPassword')}</span>
                  {showPassword ? (
                    <EyeOff aria-hidden="true" size={18} />
                  ) : (
                    <Eye aria-hidden="true" size={18} />
                  )}
                </button>
              </span>
            </div>
            <button
              className="button primary login-button"
              type="submit"
              disabled={isLoggingIn || !email.trim() || !password}
            >
              {isLoggingIn ? `${t('signingIn')}...` : t('signIn')}
            </button>
          </form>
          <p className="text-center text-sm text-muted-foreground">
            {t('newToGradSync')}{' '}
            <Link className="font-semibold text-primary" to="/register">{t('createAccount')}</Link>
          </p>
        </div>
      </section>
    </main>
  );
}
