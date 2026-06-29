import type { PropsWithChildren } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthProvider';
import { ProjectContextBanner } from '../features/projects/ProjectContextBanner';

export function Layout({ children }: PropsWithChildren) {
  const { user, logout, isLoggingOut } = useAuth();
  const navigate = useNavigate();

  async function onSignOut() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <strong>GradSync</strong>
        {user ? (
          <div className="topbar-right">
            <span className="topbar-user">{user.name}</span>
            <button
              className="button topbar-signout"
              onClick={onSignOut}
              disabled={isLoggingOut}
            >
              {isLoggingOut ? 'Signing out…' : 'Sign out'}
            </button>
          </div>
        ) : null}
      </header>
      <ProjectContextBanner />
      <main>{children}</main>
    </div>
  );
}
