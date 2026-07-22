import type { PropsWithChildren } from 'react';
import { BookOpen, BriefcaseBusiness, Code2, FileStack, FileText, LayoutDashboard, LogOut, Moon, Search, Settings, Sun, UserCircle, Users } from 'lucide-react';
import { Link, NavLink, useNavigate } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/shared/ui/primitives/tooltip';
import { cn } from '@/shared/lib/utils';
import { translateUiText } from '@/shared/i18n/translate';

import { useAuth } from '../features/auth/AuthProvider';
import { LanguageSwitcher } from '../features/i18n/LanguageSwitcher';
import { useI18n } from '../features/i18n/I18nProvider';
import { NotificationCenter } from '../features/notifications/NotificationCenter';
import { ProjectContextBanner } from '../features/projects/ProjectContextBanner';
import { useAppFeedback } from '../shared/ui/AppFeedback';

export function Layout({ children }: PropsWithChildren) {
  const { user, logout, isLoggingOut } = useAuth();
  const { theme, toggleTheme } = useAppFeedback();
  const { locale, t } = useI18n();
  const navigate = useNavigate();

  async function onSignOut() {
    await logout();
    navigate('/login');
  }

  const primaryLinks = user
    ? [
        { to: '/', label: t('dashboard'), icon: LayoutDashboard, roles: ['admin', 'advisor', 'student'] },
        { to: '/projects', label: t('projects'), icon: BriefcaseBusiness, roles: ['admin', 'advisor', 'student'] },
        { to: '/resources', label: t('resources'), icon: Settings, roles: ['admin', 'advisor', 'student'] },
        { to: '/library/papers', label: t('library'), icon: BookOpen, roles: ['admin', 'advisor', 'student'] },
        { to: '/library/code', label: t('repository'), icon: Code2, roles: ['admin', 'advisor', 'student'] },
        { to: '/library/documents', label: t('documents'), icon: FileStack, roles: ['admin', 'advisor', 'student'] },
        { to: '/writing', label: t('writing'), icon: FileText, roles: ['admin', 'advisor', 'student'] },
        { to: '/admin/accounts', label: t('team'), icon: Users, roles: ['admin'] },
        { to: '/admin/role-activations', label: t('approvals'), icon: UserCircle, roles: ['admin'] },
        { to: '/profile', label: t('profile'), icon: UserCircle, roles: ['admin', 'advisor', 'student'] },
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
              <span className="sr-only">{t('search')}</span>
              <span className="relative block">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                <Input className="pl-9" placeholder={t('globalSearchPlaceholder')} />
              </span>
            </label>
            <NotificationCenter />
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon" type="button" onClick={toggleTheme} aria-label={theme === 'dark' ? t('switchToLightTheme') : t('switchToDarkTheme')}>
                  {theme === 'dark' ? <Sun className="h-4 w-4" aria-hidden="true" /> : <Moon className="h-4 w-4" aria-hidden="true" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{theme === 'dark' ? t('switchToLightTheme') : t('switchToDarkTheme')}</TooltipContent>
            </Tooltip>
            <LanguageSwitcher />
            <div className="hidden min-w-0 text-right sm:block">
              <span className="topbar-user block truncate">{user.name}</span>
              <span className="topbar-role mt-1">{translateUiText(user.global_role, locale)}</span>
            </div>
            <Button variant="outline" onClick={onSignOut} disabled={isLoggingOut}>
              <LogOut className="h-4 w-4" aria-hidden="true" />
              {isLoggingOut ? t('signingOut') : t('signOut')}
            </Button>
          </div>
        ) : null}
      </header>
      <div className="workspace">
        {user ? (
          <aside className="sidebar" aria-label={t('workspaceNavigation')}>
            <nav className="sidebar-nav" aria-label={t('primaryWorkspace')}>
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
            <section className="sidebar-section" aria-label={t('roleWorkspace')}>
              <h2>{user.global_role === 'student' ? t('studentWork') : user.global_role === 'advisor' ? t('advisorReview') : t('administration')}</h2>
              <p>{user.global_role === 'student' ? t('studentWorkspaceDescription') : user.global_role === 'advisor' ? t('advisorWorkspaceDescription') : t('adminWorkspaceDescription')}</p>
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
