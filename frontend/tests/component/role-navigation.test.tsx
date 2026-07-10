import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Layout } from '../../src/app/Layout';
import { AuthProvider, type CurrentUser } from '../../src/features/auth/AuthProvider';
import { routeWorkspaceBundles } from '../../src/routes';
import { ProtectedRoute, RoleRoute } from '../../src/routes/ProtectedRoute';
import { DataState } from '../../src/shared/ui/DataState';
import { Button } from '../../src/shared/ui/primitives/button';
import { productionChunkSizeWarningLimit, productionManualChunks } from '../../build-guards';
import tailwindConfig from '../../tailwind.config';
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

  it('routes papers code and documents to standalone shared sections', async () => {
    mockCurrentUser({
      id: 30,
      email: 'student@test.local',
      name: 'Student',
      global_role: 'student',
      status: 'active',
    });
    renderLayout();

    await screen.findByText('student');
    expect(screen.getByRole('link', { name: 'Papers' })).toHaveAttribute('href', '/library/papers');
    expect(screen.getByRole('link', { name: 'Code' })).toHaveAttribute('href', '/library/code');
    expect(screen.getByRole('link', { name: 'Documents' })).toHaveAttribute('href', '/library/documents');
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

  it('loads route guards with shared UI dependencies from canonical boundaries', () => {
    expect(ProtectedRoute).toBeTypeOf('function');
    expect(RoleRoute).toBeTypeOf('function');
    expect(DataState).toBeTypeOf('function');
    expect(Button).toBeDefined();
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

  it('keeps large workspaces behind explicit route-level bundles', () => {
    expect(Object.keys(routeWorkspaceBundles)).toEqual([
      'accountAdmin',
      'roleActivation',
      'profile',
      'projectCreate',
      'projectDashboard',
      'projectMaterials',
      'draftSubmission',
      'weeklyReport',
      'reviewQueue',
      'writingProjects',
      'resources',
      'paperLibrary',
      'documentLibrary',
      'codeRepository',
    ]);
    expect(String(routeWorkspaceBundles.projectDashboard)).toMatch(/import\(|dynamic_import/);
    expect(String(routeWorkspaceBundles.reviewQueue)).toContain('/features/submissions/');
    expect(String(routeWorkspaceBundles.writingProjects)).toContain('/features/submissions/');
    expect(String(routeWorkspaceBundles.resources)).toContain('/features/resources/');
    expect(String(routeWorkspaceBundles.paperLibrary)).toContain('/features/library/');
    expect(String(routeWorkspaceBundles.documentLibrary)).toContain('/features/library/');
    expect(String(routeWorkspaceBundles.codeRepository)).toContain('/features/repositories/');
  });

  it('guards production bundle and Tailwind scan boundaries', () => {
    expect(productionChunkSizeWarningLimit).toBeLessThanOrEqual(450);
    expect(productionManualChunks('/repo/frontend/src/features/submissions/ReviewQueuePage.tsx')).toBe('workspace-submissions');
    expect(productionManualChunks('/repo/frontend/src/features/resources/ResourceListPage.tsx')).toBe('workspace-resources');
    expect(productionManualChunks('/repo/frontend/src/features/admin/AccountAdminPage.tsx')).toBe('workspace-admin');
    expect(productionManualChunks('/repo/frontend/node_modules/react/index.js')).toBe('vendor');

    expect(tailwindConfig.content).toContain('./src/**/*.{ts,tsx}');
    expect(tailwindConfig.content).toContain('./tests/component/**/*.{ts,tsx}');
    expect(tailwindConfig.content).not.toContain('./dist/**/*');
    expect(tailwindConfig.content).not.toContain('./node_modules/**/*');
  });
});
