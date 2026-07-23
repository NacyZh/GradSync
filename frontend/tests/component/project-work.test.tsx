import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { HomePage } from '../../src/app/HomePage';
import { AuthProvider } from '../../src/features/auth/AuthProvider';
import { ProjectSelector } from '../../src/features/projects/ProjectSelector';
import { ProjectDashboardPage } from '../../src/features/projects/ProjectDashboardPage';
import { ProjectMembersPanel } from '../../src/features/projects/ProjectMembersPanel';
import { ProjectsLandingPage } from '../../src/features/projects/ProjectsLandingPage';
import { TaskTree } from '../../src/features/tasks/TaskTree';
import { renderWithClient } from './test-utils';

describe('project work UI', () => {
  it('renders a useful application home screen', () => {
    renderWithClient(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'GradSync dashboard' })).toBeInTheDocument();
    expect(screen.getByText(/Review project work/)).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Primary actions' })).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Notifications', exact: true })).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'loading');
  });

  it('renders admin home as an operations workspace', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        if (String(url).includes('/api/accounts/me/')) {
          return new Response(
            JSON.stringify({ id: 1, email: 'admin@test.local', name: 'Admin', global_role: 'admin', status: 'active' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response(
          JSON.stringify({
            results: [{ id: 7, title: 'Graphene Lab', description: 'Materials study', status: 'active' }],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }),
    );

    renderWithClient(
      <MemoryRouter>
        <AuthProvider>
          <HomePage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'Operations workspace' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Operations queue' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Account operations' })).toHaveAttribute('href', '/admin/accounts');
    expect(screen.getByRole('link', { name: 'Role approvals' })).toHaveAttribute('href', '/admin/role-activations');
    expect(await screen.findByRole('link', { name: 'Report oversight' })).toHaveAttribute('href', '/projects/7/reports');
    expect(screen.queryByRole('heading', { name: 'Advisor work queue' })).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it('shows selected project context', () => {
    render(<ProjectSelector projects={[{ id: 1, title: 'Project A' }]} selectedProjectId={1} onSelect={() => undefined} />);

    expect(screen.getByText('Project A')).toBeInTheDocument();
  });

  it('renders projects landing with create and existing project entry for advisors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        if (String(url).includes('/api/accounts/me/')) {
          return new Response(
            JSON.stringify({ id: 2, email: 'advisor@test.local', name: 'Advisor', global_role: 'advisor', status: 'active' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response(
          JSON.stringify({
            capabilities: { canCreateProject: true },
            results: [{ id: 7, title: 'Graphene Lab', description: 'Materials study', status: 'active', startsOn: '2026-06-25' }],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }),
    );

    renderWithClient(
      <MemoryRouter>
        <AuthProvider>
          <ProjectsLandingPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'Projects' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /New project/ })).toHaveAttribute('href', '/projects/new');
    expect(screen.getByRole('link', { name: /Open/ })).toHaveAttribute('href', '/projects/7');
    vi.unstubAllGlobals();
  });

  it('renders projects landing as read-only project entry for students', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        if (String(url).includes('/api/accounts/me/')) {
          return new Response(
            JSON.stringify({ id: 3, email: 'student@test.local', name: 'Student', global_role: 'student', status: 'active' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response(
          JSON.stringify({
            capabilities: { canCreateProject: false },
            results: [{ id: 8, title: 'Assigned Project', description: '', status: 'active' }],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }),
    );

    renderWithClient(
      <MemoryRouter>
        <AuthProvider>
          <ProjectsLandingPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Assigned Project')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /New project/ })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open/ })).toHaveAttribute('href', '/projects/8');
    vi.unstubAllGlobals();
  });

  it('renders hierarchical tasks', () => {
    render(<TaskTree tasks={[{ id: 1, title: 'Parent', status: 'in_progress', children: [{ id: 2, title: 'Child', status: 'not_started', children: [] }] }]} />);

    expect(screen.getByText('Parent')).toBeInTheDocument();
    expect(screen.getByText('Child')).toBeInTheDocument();
    expect(screen.getByText('in progress')).toBeInTheDocument();
  });

  it('renders production project dashboard task, member, and review regions', async () => {
    const requests: RequestInit[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url, init) => {
        requests.push(init ?? {});
        if (String(url).includes('/api/projects/1/notifications/')) {
          return new Response(JSON.stringify({ results: [] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        if (String(url).includes('/api/projects/1/tasks/11/') && init?.method === 'DELETE') {
          return new Response(null, { status: 204 });
        }
        if (String(url).includes('/api/projects/1/tasks/11/') && init?.method === 'PATCH') {
          return new Response(JSON.stringify({
            id: 11,
            title: 'Analyze sample',
            status: 'completed',
            priority: 'high',
            description: 'Run analysis and summarize evidence.',
            assignee_id: 7,
            assignee_ids: [7, 8],
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        if (String(url).includes('/api/projects/1/tasks/') && init?.method === 'POST') {
          return new Response(JSON.stringify({ id: 21, title: 'Prepare slides', status: 'not_started', assignee_ids: [7, 8] }), {
            status: 201,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(
          JSON.stringify({
            id: 1,
            title: 'Graphene Lab',
            description: '',
            status: 'active',
            capabilities: {
              canManageProject: true,
              canEditProject: true,
              canArchiveProject: true,
              canReopenProject: false,
              canDeleteProject: true,
              canManageMembers: true,
              canCreateTasks: true,
              canUpdateTasks: true,
              deleteDisabledReason: '',
            },
            memberships: [
              { id: 1, project_id: 1, user_id: 7, nickname: 'Student One', role: 'student', status: 'active' },
              { id: 2, project_id: 1, user_id: 8, nickname: 'Student Two', role: 'student', status: 'active' },
            ],
            current_tasks: [
              {
                id: 11,
                title: 'Analyze sample',
                status: 'in_progress',
                priority: 'high',
                description: 'Run analysis and summarize evidence.',
                assignee_id: 7,
                assignee_ids: [7, 8],
                children: [{ id: 12, title: 'Draft chart', status: 'blocked', priority: 'normal', description: 'Prepare the figure for review.', children: [] }],
              },
            ],
            pending_reviews: [{ target_type: 'progress_report', target_id: 4 }],
            upcoming_bookings: [{ id: 3 }],
            activity: [{ event_type: 'pending_review_reminder', summary: 'Pending review reminder', created_at: '2026-06-25T00:00:00Z' }],
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          },
        );
      }),
    );

    renderWithClient(
      <MemoryRouter initialEntries={['/projects/1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'Graphene Lab' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Current tasks' })).toHaveTextContent('Analyze sample');
    expect(screen.getByRole('region', { name: 'Current tasks' })).not.toHaveTextContent('Student One, Student Two');
    expect(screen.getByRole('region', { name: 'Task details' })).toHaveTextContent('Priority: high');
    expect(screen.getByRole('region', { name: 'Task details' })).toHaveTextContent('Student One, Student Two');
    expect(screen.getByRole('region', { name: 'Task details' })).toHaveTextContent('Run analysis and summarize evidence.');
    const statusControl = within(screen.getByRole('region', { name: 'Task details' })).getByRole(
      'radiogroup',
      { name: 'Task status' },
    );
    expect(within(statusControl).getByRole('radio', { name: 'In progress' })).toHaveAttribute('aria-checked', 'true');
    await userEvent.click(within(statusControl).getByRole('radio', { name: 'Completed' }));
    await waitFor(() =>
      expect(within(statusControl).getByRole('radio', { name: 'Completed' })).toHaveAttribute('aria-checked', 'true'),
    );
    expect(screen.getByRole('region', { name: 'Current tasks' })).toHaveTextContent('completed');
    expect(JSON.parse(String(requests.find((request) => request.method === 'PATCH')?.body))).toEqual({
      status: 'completed',
    });
    expect(screen.getByRole('complementary', { name: 'Members and progress' })).toHaveTextContent('Student One');
    expect(screen.getByRole('button', { name: 'Add task' })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Task title'), 'Prepare slides');
    await userEvent.type(screen.getByLabelText('Task description'), 'Summarize results for group meeting.');
    await userEvent.type(screen.getByLabelText('Assignees'), 'Student');
    await userEvent.click(within(screen.getByRole('listbox', { name: 'Assignee options' })).getByRole('option', { name: 'Student One' }));
    await userEvent.type(screen.getByLabelText('Assignees'), 'Student');
    await userEvent.click(within(screen.getByRole('listbox', { name: 'Assignee options' })).getByRole('option', { name: 'Student Two' }));
    await userEvent.click(screen.getByRole('button', { name: 'Add task' }));
    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
    expect(JSON.parse(String(requests.find((request) => request.method === 'POST')?.body))).toMatchObject({
      title: 'Prepare slides',
      description: 'Summarize results for group meeting.',
      assignee_id: 7,
      assignee_ids: [7, 8],
    });
    await userEvent.click(screen.getAllByRole('button', { name: 'Delete task' })[0]);
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete task' }));
    await waitFor(() => expect(requests.some((request) => request.method === 'DELETE')).toBe(true));
    expect(screen.getByRole('button', { name: 'Archive project' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete project' })).toBeEnabled();
    expect(screen.queryByText(/Use archive for projects with research activity/)).not.toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Pending reviews' })).toHaveTextContent('Review progress_report #4');
    expect(screen.queryByRole('region', { name: 'Activity' })).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Notifications', exact: true })).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it('renders student project dashboard without management actions', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        if (String(url).includes('/api/projects/1/notifications/')) {
          return new Response(JSON.stringify({ results: [] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(
          JSON.stringify({
            id: 1,
            title: 'Student Lab',
            description: '',
            status: 'active',
            capabilities: {
              canManageProject: false,
              canEditProject: false,
              canArchiveProject: false,
              canReopenProject: false,
              canDeleteProject: false,
              canManageMembers: false,
              canCreateTasks: false,
              canUpdateTasks: false,
            },
            memberships: [{ id: 1, project_id: 1, user_id: 7, role: 'student', status: 'active' }],
            current_tasks: [{ id: 11, title: 'Read protocol', status: 'not_started', priority: 'normal', children: [] }],
            pending_reviews: [],
            upcoming_bookings: [],
            activity: [],
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          },
        );
      }),
    );

    renderWithClient(
      <MemoryRouter initialEntries={['/projects/1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'Student Lab' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Add task' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Archive project' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete project' })).not.toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Add project member' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Remove/ })).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it('keeps last dashboard data visible when live refresh becomes stale', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        if (String(url).includes('/api/projects/1/events/')) {
          return new Response(JSON.stringify({ message: 'offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        if (String(url).includes('/api/projects/1/notifications/')) {
          return new Response(JSON.stringify({ results: [] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(
          JSON.stringify({
            id: 1,
            title: 'Stable Lab',
            description: '',
            status: 'active',
            latestEventId: 'audit:1',
            memberships: [],
            current_tasks: [],
            pending_reviews: [],
            upcoming_bookings: [],
            activity: [],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }),
    );

    renderWithClient(
      <MemoryRouter initialEntries={['/projects/1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'Stable Lab' })).toBeInTheDocument();
    window.dispatchEvent(new Event('focus'));
    expect(await screen.findByText('Project data may be stale')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Stable Lab' })).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('keeps long member identity rows constrained inside the members panel', () => {
    renderWithClient(
      <ProjectMembersPanel
        projectId={1}
        canManageMembers
        members={[
          {
            id: 1,
            projectId: 1,
            userId: 11,
            nickname: 'Student With Exceptionally Long Display Name For Layout Validation',
            email: 'student.with.exceptionally.long.email.address.for.layout.validation@example.research.university.edu',
            role: 'student',
            status: 'active',
          },
        ]}
      />,
    );

    const memberRegion = screen.getByRole('region', { name: 'Project members' });
    const row = within(memberRegion).getByText(/Student With Exceptionally/).closest('li');
    expect(row).toHaveClass('min-w-0');
    expect(row).toHaveClass('overflow-hidden');
    expect(screen.getByRole('button', { name: /Remove Student With Exceptionally/ })).toBeInTheDocument();
  });

  it('submits project dates from the create form', async () => {
    const calls: unknown[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url, init) => {
        calls.push(JSON.parse(String((init as RequestInit).body)));
        return new Response(JSON.stringify({ id: 9, title: 'Dated project', description: '', status: 'active' }), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        });
      }),
    );
    const { ProjectCreatePage } = await import('../../src/features/projects/ProjectCreatePage');
    renderWithClient(
      <MemoryRouter initialEntries={['/projects/new']}>
        <Routes>
          <Route path="/projects/new" element={<ProjectCreatePage />} />
          <Route path="/projects/:projectId" element={<h1>Created project workspace</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText('Project title'), 'Dated project');
    await userEvent.type(screen.getByLabelText('Start date'), '2026-06-25');
    await userEvent.type(screen.getByLabelText('End date'), '2026-07-25');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(calls[0]).toMatchObject({ starts_on: '2026-06-25', ends_on: '2026-07-25' });
    expect(await screen.findByRole('heading', { name: 'Created project workspace' })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it('rejects an invalid project date range before submit', async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { ProjectCreatePage } = await import('../../src/features/projects/ProjectCreatePage');
    renderWithClient(
      <MemoryRouter>
        <ProjectCreatePage />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText('Project title'), 'Invalid dates');
    await userEvent.type(screen.getByLabelText('Start date'), '2026-07-25');
    await userEvent.type(screen.getByLabelText('End date'), '2026-06-25');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('Project end date cannot be before start date')).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
