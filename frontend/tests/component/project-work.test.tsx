import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { HomePage } from '../../src/app/HomePage';
import { ProjectSelector } from '../../src/features/projects/ProjectSelector';
import { ProjectDashboardPage } from '../../src/features/projects/ProjectDashboardPage';
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
    expect(screen.getByText(/Research group operations/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Resources' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'loading');
  });

  it('shows selected project context', () => {
    render(<ProjectSelector projects={[{ id: 1, title: 'Project A' }]} selectedProjectId={1} onSelect={() => undefined} />);

    expect(screen.getByText('Project A')).toBeInTheDocument();
  });

  it('renders hierarchical tasks', () => {
    render(<TaskTree tasks={[{ id: 1, title: 'Parent', status: 'in_progress', children: [{ id: 2, title: 'Child', status: 'not_started', children: [] }] }]} />);

    expect(screen.getByText('Parent')).toBeInTheDocument();
    expect(screen.getByText('Child')).toBeInTheDocument();
    expect(screen.getByText('in progress')).toBeInTheDocument();
  });

  it('renders production project dashboard task, member, review, and activity regions', async () => {
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
            title: 'Graphene Lab',
            description: '',
            status: 'active',
            memberships: [{ id: 1, project_id: 1, user_id: 7, role: 'student', status: 'active' }],
            current_tasks: [
              {
                id: 11,
                title: 'Analyze sample',
                status: 'in_progress',
                priority: 'high',
                assignee_id: 7,
                children: [{ id: 12, title: 'Draft chart', status: 'blocked', priority: 'normal', children: [] }],
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
    expect(screen.getByRole('region', { name: 'Task details' })).toHaveTextContent('Priority: high');
    expect(screen.getByRole('complementary', { name: 'Members and progress' })).toHaveTextContent('User 7');
    expect(screen.getByRole('region', { name: 'Pending reviews' })).toHaveTextContent('Review progress_report #4');
    expect(screen.getByRole('region', { name: 'Activity' })).toHaveTextContent('Pending review reminder');
    vi.unstubAllGlobals();
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
    renderWithClient(<ProjectCreatePage />);

    await userEvent.type(screen.getByLabelText('Project title'), 'Dated project');
    await userEvent.type(screen.getByLabelText('Start date'), '2026-06-25');
    await userEvent.type(screen.getByLabelText('End date'), '2026-07-25');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(calls[0]).toMatchObject({ starts_on: '2026-06-25', ends_on: '2026-07-25' });
    vi.unstubAllGlobals();
  });

  it('rejects an invalid project date range before submit', async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { ProjectCreatePage } = await import('../../src/features/projects/ProjectCreatePage');
    renderWithClient(<ProjectCreatePage />);

    await userEvent.type(screen.getByLabelText('Project title'), 'Invalid dates');
    await userEvent.type(screen.getByLabelText('Start date'), '2026-07-25');
    await userEvent.type(screen.getByLabelText('End date'), '2026-06-25');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Project end date cannot be before start date');
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
