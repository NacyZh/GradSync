import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Layout } from '../../src/app/Layout';
import { AuthProvider, type CurrentUser } from '../../src/features/auth/AuthProvider';
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
    expect(screen.getByRole('link', { name: 'Accounts' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'New Project' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
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
    expect(screen.getByRole('link', { name: 'New Project' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Accounts' })).not.toBeInTheDocument();
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
    expect(screen.queryByRole('link', { name: 'New Project' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Accounts' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Resources' })).toBeInTheDocument();
  });

  it('shows no nav links when unauthenticated', async () => {
    mockCurrentUser(null);
    renderLayout();

    await screen.findByText('content');
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });
});
