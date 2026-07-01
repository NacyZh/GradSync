import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import { useAuth } from '../features/auth/AuthProvider';
import { listProjects } from '../features/projects/api';
import { AsyncState } from '../shared/ui/AsyncState';

export function HomePage() {
  const { user, isLoading: isLoadingUser } = useAuth();
  const projectsQuery = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
    enabled: Boolean(user),
  });

  const projects = projectsQuery.data?.results ?? [];
  const role = user?.global_role;

  return (
    <>
      <section className="page-heading dashboard-hero">
        <div>
          <h1>{role === 'student' ? 'Student workspace' : role === 'advisor' ? 'Advisor workspace' : 'GradSync dashboard'}</h1>
          <p>Research group operations for projects, reviews, reports, bookings, and reminders.</p>
        </div>
        <nav aria-label="Primary actions" className="action-row">
          {(role === 'admin' || role === 'advisor') ? (
            <Button asChild><Link to="/projects/new">New project</Link></Button>
          ) : null}
          {role === 'admin' ? (
            <Button asChild variant="outline"><Link to="/admin/accounts">Manage accounts</Link></Button>
          ) : null}
          <Button asChild variant="outline"><Link to="/resources">Resources</Link></Button>
        </nav>
      </section>

      {isLoadingUser ? <AsyncState state="loading" message="Loading account" /> : null}

      {user && (
        <section className="dashboard-grid" aria-label="Application overview">
          <Card>
            <CardHeader>
              <CardDescription>Projects</CardDescription>
              <CardTitle className="text-2xl">{projects.length}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">visible workspaces</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Pending reviews</CardDescription>
              <CardTitle className="text-2xl">{role === 'student' ? 'Track' : 'Review'}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{role === 'student' ? 'drafts and reports' : 'student submissions'}</CardContent>
          </Card>
          <Card id="notifications">
            <CardHeader>
              <CardDescription>Notifications</CardDescription>
              <CardTitle className="text-2xl">Live</CardTitle>
            </CardHeader>
            <CardContent><Badge variant="success">delivery status and reminders</Badge></CardContent>
          </Card>
          <article className="panel">
            <h2>Your projects</h2>
            {projectsQuery.isLoading ? <AsyncState state="loading" message="Loading projects" /> : null}
            {projectsQuery.error ? (
              <AsyncState state="error" message={projectsQuery.error.message} />
            ) : null}
            {!projectsQuery.isLoading && !projectsQuery.error && projects.length === 0 ? (
              <AsyncState state="empty" message="No visible projects yet" />
            ) : null}
            {projects.length > 0 ? (
              <ul className="project-list">
                {projects.map((project) => (
                  <li key={project.id}>
                    <Link to={`/projects/${project.id}`}>
                      <span>{project.title}</span>
                      <small>{project.status}</small>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
          {role === 'student' ? (
            <article className="panel">
              <h2>Next actions</h2>
              <div className="workflow-list">
                {projects[0] ? <Link to={`/projects/${projects[0].id}/drafts`}>Submit a draft</Link> : null}
                {projects[0] ? <Link to={`/projects/${projects[0].id}/reports`}>Weekly reports</Link> : null}
                <Link to="/resources">Book a resource</Link>
              </div>
            </article>
          ) : (
            <article className="panel">
              <h2>Review workflow</h2>
              <div className="workflow-list">
                <Link to="/projects/new">Create project and memberships</Link>
                <Link to="/resources">Reserve lab equipment or seats</Link>
                {projects[0] ? <Link to={`/projects/${projects[0].id}/reviews`}>Open review queue</Link> : null}
              </div>
            </article>
          )}

          <article className="panel">
            <h2>System status</h2>
            <dl className="status-list">
              <div>
                <dt>Account</dt>
                <dd>{user.email}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{user.global_role}</dd>
              </div>
              <div>
                <dt>Visible projects</dt>
                <dd>{projects.length}</dd>
              </div>
            </dl>
          </article>
        </section>
      )}
    </>
  );
}
