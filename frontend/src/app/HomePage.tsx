import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

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
          <p>{role === 'student' ? 'Open assigned projects and continue submission work.' : 'Review project work and keep active research moving.'}</p>
        </div>
      </section>

      {isLoadingUser ? <AsyncState state="loading" message="Loading account" /> : null}

      {user && (
        <section className="grid gap-4 xl:grid-cols-[minmax(24rem,1.25fr)_minmax(18rem,0.75fr)]" aria-label="Dashboard work overview">
          <article className="panel">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2>Your projects</h2>
                <p className="text-sm text-muted-foreground">{projects.length} visible workspaces</p>
              </div>
              {(role === 'admin' || role === 'advisor') ? (
                <Link className="inline-action font-bold text-primary" to="/projects/new">New project</Link>
              ) : null}
            </div>
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
              <h2>Student work queue</h2>
              <div className="workflow-list">
                {projects[0] ? <Link to={`/projects/${projects[0].id}/drafts`}>Submit a draft</Link> : null}
                {projects[0] ? <Link to={`/projects/${projects[0].id}/reports`}>Weekly reports</Link> : null}
                <Link to="/resources">Book a resource</Link>
              </div>
            </article>
          ) : (
            <article className="panel">
              <h2>Advisor work queue</h2>
              <div className="workflow-list">
                <Link to="/resources">Reserve lab equipment or seats</Link>
                {projects[0] ? <Link to={`/projects/${projects[0].id}/reviews`}>Open review queue</Link> : null}
                {projects[0] ? <Link to={`/projects/${projects[0].id}`}>Open project dashboard</Link> : null}
              </div>
            </article>
          )}
        </section>
      )}
    </>
  );
}
