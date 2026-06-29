import type { PropsWithChildren } from 'react';
import { Link, useNavigate } from 'react-router-dom';

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
        <Link to="/" className="topbar-brand">
          GradSync
        </Link>
        {user ? (
          <div className="topbar-right">
            <nav aria-label="Main navigation" className="topbar-nav">
              {user.global_role === 'admin' ? (
                <Link to="/admin/accounts">Accounts</Link>
              ) : null}
              {(user.global_role === 'admin' || user.global_role === 'advisor') ? (
                <>
                  <Link to="/projects/new">New Project</Link>
                  <Link to="/resources">Resources</Link>
                </>
              ) : null}
              {user.global_role === 'student' ? (
                <>
                  <Link to="/resources">Resources</Link>
                </>
              ) : null}
            </nav>
            <span className="topbar-user">{user.name}</span>
            <span className="topbar-role">{user.global_role}</span>
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
