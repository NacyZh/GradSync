import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Layout } from '../../src/app/Layout';
import { AuthProvider, type CurrentUser } from '../../src/features/auth/AuthProvider';
import { ProtectedRoute, RoleRoute } from '../../src/routes/ProtectedRoute';
import { renderWithClient } from './test-utils';

function mockCurrentUser(user: CurrentUser | null) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => {
      if (user) {
        return Promise.resolve(
          new Response(JSON.stringify(user), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ message: 'Authentication required' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }),
  );
}

function renderLayout() {
  return renderWithClient(
    <MemoryRouter>
      <AuthProvider>
        <Layout>content</Layout>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe('role-aware navigation', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows account management and project links for admin', async () => {
    mockCurrentUser({
      id: 1,
      email: 'admin@test.local',
      name: 'Admin',
      global_role: 'admin',
      status: 'active',
    });
    renderLayout();

    await screen.findByText('admin');
    expect(screen.getByRole('link', { name: 'Team' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Projects' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open notifications' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Switch to dark theme' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('main')).toHaveTextContent('content');
    expect(screen.getByLabelText('Workspace navigation')).toBeInTheDocument();
  });

  it('shows project links for advisor but no account admin', async () => {
    mockCurrentUser({
      id: 2,
      email: 'advisor@test.local',
      name: 'Advisor',
      global_role: 'advisor',
      status: 'active',
    });
    renderLayout();

    await screen.findByText('advisor');
    expect(screen.getByRole('link', { name: 'Projects' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Team' })).not.toBeInTheDocument();
  });

  it('hides project creation and account admin from student', async () => {
    mockCurrentUser({
      id: 3,
      email: 'student@test.local',
      name: 'Student',
      global_role: 'student',
      status: 'active',
    });
    renderLayout();

    await screen.findByText('student');
    expect(screen.queryByRole('link', { name: 'Projects' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Team' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Resources' })).toBeInTheDocument();
  });

  it('toggles the persisted theme from the workspace shell', async () => {
    const user = userEvent.setup();
    mockCurrentUser({
      id: 4,
      email: 'advisor@test.local',
      name: 'Advisor',
      global_role: 'advisor',
      status: 'active',
    });
    renderLayout();

    await screen.findByText('advisor');
    await user.click(screen.getByRole('button', { name: 'Switch to dark theme' }));
    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('renders protected route content for authenticated users', async () => {
    mockCurrentUser({
      id: 5,
      email: 'student@test.local',
      name: 'Student',
      global_role: 'student',
      status: 'active',
    });
    renderWithClient(
      <MemoryRouter>
        <AuthProvider>
          <ProtectedRoute>protected content</ProtectedRoute>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText('protected content')).toBeInTheDocument();
  });

  it('redirects users away from disallowed role routes', async () => {
    mockCurrentUser({
      id: 6,
      email: 'student@test.local',
      name: 'Student',
      global_role: 'student',
      status: 'active',
    });
    renderWithClient(
      <MemoryRouter>
        <AuthProvider>
          <RoleRoute allowedRoles={['admin']}>admin content</RoleRoute>
        </AuthProvider>
      </MemoryRouter>,
    );

    await screen.findByText('Loading account');
    expect(screen.queryByText('admin content')).not.toBeInTheDocument();
  });

  it('shows no nav links when unauthenticated', async () => {
    mockCurrentUser(null);
    renderLayout();

    await screen.findByText('content');
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });
});
