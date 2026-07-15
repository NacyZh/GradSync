import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ProjectMembersPanel } from '../../src/features/projects/ProjectMembersPanel';
import { ProjectCreatePage } from '../../src/features/projects/ProjectCreatePage';
import { renderWithClient } from './test-utils';

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const payload = handler(String(input), init);
    if (init?.method === 'DELETE') {
      return new Response(null, { status: 204 });
    }
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;
}

describe('collaboration project members UI', () => {
  it('adds students through nickname search and disambiguates duplicate nicknames', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (url.includes('/api/accounts/students/')) {
        return [
          { id: 7, nickname: 'Alex', email: 'alex.one@example.edu', degreeType: 'masters', label: 'Alex <alex.one@example.edu>' },
          { id: 8, nickname: 'Alex', email: 'alex.two@example.edu', degreeType: 'doctoral', label: 'Alex <alex.two@example.edu>' },
        ];
      }
      return {
        id: 12,
        projectId: 1,
        userId: 8,
        nickname: 'Alex',
        email: 'alex.two@example.edu',
        role: 'student',
        status: 'active',
      };
    });

    renderWithClient(<ProjectMembersPanel projectId={1} members={[]} />);

    await userEvent.type(screen.getByLabelText('Student nickname'), 'Alex');
    expect(await screen.findByText('alex.one@example.edu')).toBeInTheDocument();
    expect(screen.getByText('doctoral')).toBeInTheDocument();
    await userEvent.click(screen.getByText('alex.two@example.edu'));

    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
    expect(await screen.findByText('Member added')).toBeInTheDocument();
    expect(JSON.parse(String(requests.find((request) => request.method === 'POST')?.body))).toEqual({ studentId: 8 });
  });

  it('shows active and removed states and confirms removal', async () => {
    const requests: RequestInit[] = [];
    mockFetch((_url, init) => {
      requests.push(init ?? {});
      return {};
    });
    renderWithClient(
      <ProjectMembersPanel
        projectId={1}
        members={[
          { id: 1, projectId: 1, userId: 10, nickname: 'Teacher', email: 'teacher@example.edu', role: 'advisor', status: 'active' },
          { id: 2, projectId: 1, userId: 11, nickname: 'Student', email: 'student@example.edu', role: 'student', status: 'active' },
          { id: 3, projectId: 1, userId: 12, nickname: 'Removed', email: 'removed@example.edu', role: 'student', status: 'removed' },
        ]}
      />,
    );

    const memberRegion = screen.getByRole('region', { name: 'Project members' });
    expect(within(memberRegion).getByText('student@example.edu')).toBeInTheDocument();
    expect(within(memberRegion).getByText('removed')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Remove Student' }));
    const dialog = screen.getByRole('dialog', { name: 'Remove student?' });
    expect(dialog).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Remove student' }));

    await waitFor(() => expect(requests.some((request) => request.method === 'DELETE')).toBe(true));
    expect(await screen.findByText('Member removed')).toBeInTheDocument();
  });

  it('explains when no eligible students match the selector query', async () => {
    mockFetch(() => []);
    renderWithClient(<ProjectMembersPanel projectId={1} members={[]} />);

    await userEvent.type(screen.getByLabelText('Student nickname'), 'No Match');

    expect(await screen.findByText('No eligible students match this search.')).toBeInTheDocument();
  });

  it('creates a project from selected student account options', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (url.includes('/api/accounts/students/')) {
        return [
          { id: 7, nickname: 'Alex', email: 'alex.one@example.edu', degreeType: 'masters', label: 'Alex <alex.one@example.edu>' },
          { id: 8, nickname: 'Alex', email: 'alex.two@example.edu', degreeType: 'doctoral', label: 'Alex <alex.two@example.edu>' },
        ];
      }
      return { id: 44, title: 'Dropdown Project', description: '', status: 'active' };
    });

    renderWithClient(<ProjectCreatePage />);

    await userEvent.type(screen.getByLabelText('Project title'), 'Dropdown Project');
    await userEvent.type(screen.getByLabelText('Student nickname'), 'Alex');
    expect(await screen.findByText('alex.one@example.edu')).toBeInTheDocument();
    await userEvent.click(screen.getByText('alex.two@example.edu'));
    expect(screen.getByRole('list', { name: 'Selected students' })).toHaveTextContent('Alex <alex.two@example.edu>');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
    const body = JSON.parse(String(requests.find((request) => request.method === 'POST')?.body));
    expect(body).toMatchObject({ title: 'Dropdown Project', student_ids: [8] });
  });

  it('blocks duplicate selected students in project creation selector', async () => {
    mockFetch((url) => {
      if (url.includes('/api/accounts/students/')) {
        return [{ id: 7, nickname: 'Alex', email: 'alex.one@example.edu', degreeType: 'masters', label: 'Alex <alex.one@example.edu>' }];
      }
      return { id: 44, title: 'Dropdown Project', description: '', status: 'active' };
    });

    renderWithClient(<ProjectCreatePage />);

    await userEvent.type(screen.getByLabelText('Student nickname'), 'Alex');
    await userEvent.click(await screen.findByText('alex.one@example.edu'));

    expect(screen.getByRole('button', { name: /alex.one@example.edu/ })).toBeDisabled();
    expect(screen.getByText('Selected')).toBeInTheDocument();
  });
});
