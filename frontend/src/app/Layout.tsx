import type { PropsWithChildren } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthProvider';
import { ProjectContextBanner } from '../features/projects/ProjectContextBanner';
import { useAppFeedback } from '../shared/ui/AppFeedback';

export function Layout({ children }: PropsWithChildren) {
  const { user, logout, isLoggingOut } = useAuth();
  const { theme, toggleTheme } = useAppFeedback();
  const navigate = useNavigate();

  async function onSignOut() {
    await logout();
    navigate('/login');
  }

  const primaryLinks = user
    ? [
        { to: '/', label: 'Dashboard', roles: ['admin', 'advisor', 'student'] },
        { to: '/projects/new', label: 'Projects', roles: ['admin', 'advisor'] },
        { to: '/resources', label: 'Resources', roles: ['admin', 'advisor', 'student'] },
        { to: '/admin/accounts', label: 'Team', roles: ['admin'] },
      ].filter((link) => link.roles.includes(user.global_role))
    : [];

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="topbar-brand">
          <span className="brand-mark">GS</span>
          <span>GradSync</span>
        </Link>
        {user ? (
          <div className="topbar-right">
            <label className="global-search">
              <span>Search</span>
              <input placeholder="Search projects, tasks, reviews" />
            </label>
            <Link className="icon-button notification-button" to="/#notifications" aria-label="Open notifications">
              <span aria-hidden="true">!</span>
              <span className="unread-dot" aria-hidden="true" />
            </Link>
            <button className="icon-button" type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
              {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
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
      <div className="workspace">
        {user ? (
          <aside className="sidebar" aria-label="Workspace navigation">
            <nav className="sidebar-nav" aria-label="Primary workspace">
              {primaryLinks.map((link) => (
                <NavLink key={link.to} to={link.to} end={link.to === '/'}>
                  {link.label}
                </NavLink>
              ))}
            </nav>
            <section className="sidebar-section" aria-label="Role workspace">
              <h2>{user.global_role === 'student' ? 'Student work' : user.global_role === 'advisor' ? 'Advisor review' : 'Administration'}</h2>
              <p>{user.global_role === 'student' ? 'Submit work, track reviews, and reserve resources.' : user.global_role === 'advisor' ? 'Review submissions, manage tasks, and monitor project progress.' : 'Manage accounts, projects, and release readiness.'}</p>
            </section>
          </aside>
        ) : null}
        <div className="content-shell">
          <ProjectContextBanner />
          <main>{children}</main>
        </div>
      </div>
    </div>
  );
}
