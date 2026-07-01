import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

import { StatusBadge } from './StatusBadge';

type ProjectContextBarProps = {
  projectId: number;
  title?: string;
  status?: string;
  isLoading?: boolean;
  className?: string;
};

const workflowLinks = [
  ['Dashboard', ''],
  ['Drafts', 'drafts'],
  ['Reports', 'reports'],
  ['Reviews', 'reviews'],
  ['Resources', 'resources'],
] as const;

export function ProjectContextBar({ projectId, title, status, isLoading, className }: ProjectContextBarProps) {
  return (
    <section
      aria-label="Selected project context"
      className={cn('flex flex-wrap items-center gap-3 border-b bg-muted px-4 py-3 text-sm md:px-7', className)}
    >
      <span className="font-bold text-muted-foreground">Selected project</span>
      {isLoading ? <Skeleton className="h-5 w-40" /> : <strong>{title ?? `Project ${projectId}`}</strong>}
      {status ? <StatusBadge status={status} /> : null}
      <nav aria-label="Project workflow" className="ml-auto flex flex-wrap gap-2">
        {workflowLinks.map(([label, suffix]) => (
          <Button key={label} asChild variant="ghost" size="sm">
            <Link to={`/projects/${projectId}${suffix ? `/${suffix}` : ''}`}>{label}</Link>
          </Button>
        ))}
      </nav>
    </section>
  );
}
