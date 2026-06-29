import type { ReactElement } from 'react';
import { createBrowserRouter } from 'react-router-dom';

import { HomePage } from '../app/HomePage';
import { Layout } from '../app/Layout';
import { AccountAdminPage } from '../features/admin/AccountAdminPage';
import { LoginPage } from '../features/auth/LoginPage';
import { ProjectCreatePage } from '../features/projects/ProjectCreatePage';
import { ProjectDashboardPage } from '../features/projects/ProjectDashboardPage';
import { DraftSubmissionPage } from '../features/submissions/DraftSubmissionPage';
import { ReviewQueuePage } from '../features/submissions/ReviewQueuePage';
import { WeeklyReportPage } from '../features/submissions/WeeklyReportPage';
import { ResourceListPage } from '../features/resources/ResourceListPage';
import { ProtectedRoute, RoleRoute } from './ProtectedRoute';

function protectedPage(page: ReactElement) {
  return (
    <ProtectedRoute>
      <Layout>{page}</Layout>
    </ProtectedRoute>
  );
}

/** Wrap a page so only the listed roles can access it. */
function rolePage(page: ReactElement, ...allowedRoles: ('admin' | 'advisor' | 'student')[]) {
  return (
    <ProtectedRoute>
      <RoleRoute allowedRoles={allowedRoles}>
        <Layout>{page}</Layout>
      </RoleRoute>
    </ProtectedRoute>
  );
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <HomePage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  // Admin-only: account management.
  {
    path: '/admin/accounts',
    element: rolePage(<AccountAdminPage />, 'admin'),
  },
  // Advisor + Admin: create and manage projects.
  {
    path: '/projects/new',
    element: rolePage(<ProjectCreatePage />, 'admin', 'advisor'),
  },
  // All roles: view project dashboards.
  {
    path: '/projects/:projectId',
    element: protectedPage(<ProjectDashboardPage />),
  },
  {
    path: '/projects/:projectId/drafts',
    element: protectedPage(<DraftSubmissionPage />),
  },
  {
    path: '/projects/:projectId/reports',
    element: protectedPage(<WeeklyReportPage />),
  },
  {
    path: '/projects/:projectId/reviews',
    element: protectedPage(<ReviewQueuePage />),
  },
  {
    path: '/projects/:projectId/resources',
    element: protectedPage(<ResourceListPage />),
  },
  {
    path: '/resources',
    element: protectedPage(<ResourceListPage />),
  },
]);
