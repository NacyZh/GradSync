import { lazy, Suspense, type ReactElement } from 'react';
import { createBrowserRouter } from 'react-router-dom';

import { HomePage } from '../app/HomePage';
import { Layout } from '../app/Layout';
import { LoginPage } from '../features/auth/LoginPage';
import { DataState } from '../shared/ui/DataState';
import { ProtectedRoute, RoleRoute } from './ProtectedRoute';

export const routeWorkspaceBundles = {
  accountAdmin: () => import('../features/admin/AccountAdminPage'),
  projectCreate: () => import('../features/projects/ProjectCreatePage'),
  projectDashboard: () => import('../features/projects/ProjectDashboardPage'),
  draftSubmission: () => import('../features/submissions/DraftSubmissionPage'),
  weeklyReport: () => import('../features/submissions/WeeklyReportPage'),
  reviewQueue: () => import('../features/submissions/ReviewQueuePage'),
  resources: () => import('../features/resources/ResourceListPage'),
} as const;

const AccountAdminPage = lazy(async () => ({ default: (await routeWorkspaceBundles.accountAdmin()).AccountAdminPage }));
const ProjectCreatePage = lazy(async () => ({ default: (await routeWorkspaceBundles.projectCreate()).ProjectCreatePage }));
const ProjectDashboardPage = lazy(async () => ({ default: (await routeWorkspaceBundles.projectDashboard()).ProjectDashboardPage }));
const DraftSubmissionPage = lazy(async () => ({ default: (await routeWorkspaceBundles.draftSubmission()).DraftSubmissionPage }));
const WeeklyReportPage = lazy(async () => ({ default: (await routeWorkspaceBundles.weeklyReport()).WeeklyReportPage }));
const ReviewQueuePage = lazy(async () => ({ default: (await routeWorkspaceBundles.reviewQueue()).ReviewQueuePage }));
const ResourceListPage = lazy(async () => ({ default: (await routeWorkspaceBundles.resources()).ResourceListPage }));

function routeContent(page: ReactElement) {
  return (
    <Suspense fallback={<DataState state="loading" title="Loading workspace" message="Preparing the requested workspace." />}>
      {page}
    </Suspense>
  );
}

function protectedPage(page: ReactElement) {
  return (
    <ProtectedRoute>
      <Layout>{routeContent(page)}</Layout>
    </ProtectedRoute>
  );
}

/** Wrap a page so only the listed roles can access it. */
function rolePage(page: ReactElement, ...allowedRoles: ('admin' | 'advisor' | 'student')[]) {
  return (
    <ProtectedRoute>
      <RoleRoute allowedRoles={allowedRoles}>
        <Layout>{routeContent(page)}</Layout>
      </RoleRoute>
    </ProtectedRoute>
  );
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: protectedPage(<HomePage />),
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
