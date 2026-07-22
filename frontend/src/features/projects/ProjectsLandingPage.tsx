import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';
import { formatUiDate } from '@/shared/i18n/translate';

import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { useAuth } from '../auth/AuthProvider';
import { listProjects } from './api';
import { useProjectLiveRefresh } from './useProjectLiveRefresh';

export function ProjectsLandingPage() {
  const { user } = useAuth();
  const projectsQuery = useQuery({ queryKey: ['projects'], queryFn: listProjects });
  const projects = projectsQuery.data?.results ?? [];
  const liveRefresh = useProjectLiveRefresh(projects[0]?.id);
  const canCreateProject =
    projectsQuery.data?.capabilities?.canCreateProject ??
    (user?.global_role === 'admin' || user?.global_role === 'advisor');

  return (
    <PageShell
      title="Projects"
      description="Open existing project workspaces or create a new project."
      actions={
        canCreateProject ? (
          <Button asChild>
            <Link to="/projects/new">
              <Plus className="h-4 w-4" aria-hidden="true" />
              New project
            </Link>
          </Button>
        ) : null
      }
    >
      {projectsQuery.isLoading ? <DataState state="loading" title="Loading projects" message="Loading visible projects..." /> : null}
      {projectsQuery.error ? <DataState state="error" title="Projects unavailable" message={projectsQuery.error.message} /> : null}
      {liveRefresh.state === 'stale' ? (
        <DataState state="warning" title="Project list may be stale" message="Last successful project list is still visible while live refresh retries." />
      ) : null}
      {!projectsQuery.isLoading && !projectsQuery.error && projects.length === 0 ? (
        <DataState state="empty" title="No visible projects" message="Projects assigned to this account will appear here." />
      ) : null}
      {projects.length ? (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Visible projects">
          {projects.map((project) => (
            <Card key={project.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>{project.title}</CardTitle>
                    <CardDescription>{project.description || 'Project workspace'}</CardDescription>
                  </div>
                  <StatusBadge status={project.status} />
                </div>
              </CardHeader>
              <CardContent className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">{formatRange(project.startsOn ?? project.starts_on, project.endsOn ?? project.ends_on)}</span>
                <Button asChild variant="outline" size="sm">
                  <Link to={`/projects/${project.id}`}>
                    Open
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}
    </PageShell>
  );
}

function formatRange(startsOn?: string | null, endsOn?: string | null) {
  if (!startsOn && !endsOn) return 'No dates set';
  if (startsOn && endsOn) return `${formatDate(startsOn)} - ${formatDate(endsOn)}`;
  return startsOn ? `Starts ${formatDate(startsOn)}` : `Ends ${formatDate(endsOn)}`;
}

function formatDate(value?: string | null) {
  if (!value) return 'No date';
  return formatUiDate(value, { month: 'short', day: 'numeric', year: 'numeric' });
}
