import type { PropsWithChildren } from 'react';
import { Bell, BookOpen, BriefcaseBusiness, Code2, FileStack, FileText, LayoutDashboard, LogOut, Moon, Search, Settings, Sun, UserCircle, Users } from 'lucide-react';
import { Link, NavLink, useNavigate } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/shared/ui/primitives/tooltip';
import { cn } from '@/shared/lib/utils';

import { useAuth } from '../features/auth/AuthProvider';
import { LanguageSwitcher } from '../features/i18n/LanguageSwitcher';
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
        { to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'advisor', 'student'] },
        { to: '/projects', label: 'Projects', icon: BriefcaseBusiness, roles: ['admin', 'advisor', 'student'] },
        { to: '/resources', label: 'Resources', icon: Settings, roles: ['admin', 'advisor', 'student'] },
        { to: '/library/papers', label: 'Papers', icon: BookOpen, roles: ['admin', 'advisor', 'student'] },
        { to: '/library/code', label: 'Code', icon: Code2, roles: ['admin', 'advisor', 'student'] },
        { to: '/library/documents', label: 'Documents', icon: FileStack, roles: ['admin', 'advisor', 'student'] },
        { to: '/writing', label: 'Writing', icon: FileText, roles: ['admin', 'advisor', 'student'] },
        { to: '/admin/accounts', label: 'Team', icon: Users, roles: ['admin'] },
        { to: '/admin/role-activations', label: 'Approvals', icon: UserCircle, roles: ['admin'] },
        { to: '/profile', label: 'Profile', icon: UserCircle, roles: ['admin', 'advisor', 'student'] },
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
              <span className="sr-only">Search</span>
              <span className="relative block">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                <Input className="pl-9" placeholder="Search projects, tasks, reviews" />
              </span>
            </label>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button asChild variant="outline" size="icon" className="relative" aria-label="Open notifications">
                  <Link to="/#notifications">
                    <Bell className="h-4 w-4" aria-hidden="true" />
                    <span className="unread-dot" aria-hidden="true" />
                  </Link>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Open notifications</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon" type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
                  {theme === 'dark' ? <Sun className="h-4 w-4" aria-hidden="true" /> : <Moon className="h-4 w-4" aria-hidden="true" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}</TooltipContent>
            </Tooltip>
            <LanguageSwitcher />
            <div className="hidden min-w-0 text-right sm:block">
              <span className="topbar-user block truncate">{user.name}</span>
              <span className="topbar-role mt-1">{user.global_role}</span>
            </div>
            <Button variant="outline" onClick={onSignOut} disabled={isLoggingOut}>
              <LogOut className="h-4 w-4" aria-hidden="true" />
              {isLoggingOut ? 'Signing out' : 'Sign out'}
            </Button>
          </div>
        ) : null}
      </header>
      <div className="workspace">
        {user ? (
          <aside className="sidebar" aria-label="Workspace navigation">
            <nav className="sidebar-nav" aria-label="Primary workspace">
              {primaryLinks.map(({ icon: Icon, ...link }) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === '/'}
                  className={({ isActive }) => cn(isActive && 'active')}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  <span>{link.label}</span>
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
          <main>{children}</main>
        </div>
      </div>
    </div>
  );
}
