import { useState } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuth } from './AuthProvider';
import { Layout } from '../../app/Layout';
import { AsyncState } from '../../shared/ui/AsyncState';
import { FormStatus } from '../../shared/ui/FormStatus';

export function LoginPage() {
  const { user, isLoading, login, isLoggingIn, loginError } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  if (isLoading) {
    return (
      <Layout>
        <AsyncState state="loading" message="Loading account" />
      </Layout>
    );
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
    <Layout>
      <section className="login-container">
        <div className="login-card">
          <h1>GradSync</h1>
          <p className="login-subtitle">Sign in to your research group account</p>

          <form aria-label="Sign in" onSubmit={onSubmit} className="login-form">
            <label>
              Email
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoggingIn}
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoggingIn}
              />
            </label>
            <button
              className="button primary login-button"
              type="submit"
              disabled={isLoggingIn || !email.trim() || !password}
            >
              {isLoggingIn ? 'Signing in…' : 'Sign in'}
            </button>
            <FormStatus error={loginError ?? undefined} />
          </form>
        </div>
      </section>
    </Layout>
  );
}
