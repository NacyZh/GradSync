import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthProvider';
import { listProjects } from '../features/projects/api';
import { AsyncState } from '../shared/ui/AsyncState';
import { Layout } from './Layout';

export function HomePage() {
  const { user, isLoading: isLoadingUser } = useAuth();
  const projectsQuery = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
    enabled: Boolean(user),
  });

  const projects = projectsQuery.data?.results ?? [];

  return (
    <Layout>
      <section className="page-heading">
        <div>
          <h1>GradSync</h1>
          <p>Research group operations for projects, reviews, reports, bookings, and reminders.</p>
        </div>
        <nav aria-label="Primary actions" className="action-row">
          <Link className="button primary" to="/projects/new">
            New project
          </Link>
          <Link className="button" to="/resources">
            Resources
          </Link>
        </nav>
      </section>

      {isLoadingUser ? <AsyncState state="loading" message="Loading account" /> : null}

      {user && (
        <section className="dashboard-grid" aria-label="Application overview">
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

          <article className="panel">
            <h2>Workflow</h2>
            <div className="workflow-list">
              <Link to="/projects/new">Create project and memberships</Link>
              <Link to="/resources">Reserve lab equipment or seats</Link>
              {projects[0] ? <Link to={`/projects/${projects[0].id}/reviews`}>Open review queue</Link> : null}
            </div>
          </article>

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
    </Layout>
  );
}
