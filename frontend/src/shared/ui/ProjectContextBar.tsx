import { NavLink } from 'react-router-dom';
import { ClipboardList, FileStack, FileText, Gauge, Inbox, Microscope } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { cn } from '@/shared/lib/utils';

type ProjectContextBarProps = {
  projectId: number;
  title?: string;
  status?: string;
  userRole?: UserRole;
  isLoading?: boolean;
  className?: string;
};

type UserRole = 'admin' | 'advisor' | 'student';

const workflowLinks: Array<{
  label: string;
  suffix: string;
  icon: typeof Gauge;
  roles: UserRole[];
}> = [
  { label: 'Dashboard', suffix: '', icon: Gauge, roles: ['admin', 'advisor', 'student'] },
  { label: 'Materials', suffix: 'materials', icon: FileStack, roles: ['admin', 'advisor', 'student'] },
  { label: 'Drafts', suffix: 'drafts', icon: FileText, roles: ['admin', 'student'] },
  { label: 'Reports', suffix: 'reports', icon: ClipboardList, roles: ['admin', 'student'] },
  { label: 'Reviews', suffix: 'reviews', icon: Inbox, roles: ['admin', 'advisor'] },
  { label: 'Resources', suffix: 'resources', icon: Microscope, roles: ['admin', 'advisor', 'student'] },
];

export function ProjectContextBar({ projectId, userRole = 'student', className }: ProjectContextBarProps) {
  const links = workflowLinks.filter((link) => link.roles.includes(userRole));

  return (
    <section
      aria-label="Project workspace navigation"
      className={cn('mb-5 rounded-lg border bg-card px-3 py-2 shadow-sm md:px-4', className)}
    >
      <nav aria-label="Project workflow" className="flex flex-wrap items-center justify-end gap-2">
        {links.map(({ label, suffix, icon: Icon }) => (
          <Button key={label} asChild variant="ghost" size="sm">
            <NavLink
              to={`/projects/${projectId}${suffix ? `/${suffix}` : ''}`}
              end={suffix === ''}
              className={({ isActive }) => cn('gap-2', isActive && 'bg-accent text-accent-foreground')}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </NavLink>
          </Button>
        ))}
      </nav>
    </section>
  );
}
