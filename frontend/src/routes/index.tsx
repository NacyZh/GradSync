import type { ReactElement } from 'react';
import { createBrowserRouter } from 'react-router-dom';

import { HomePage } from '../app/HomePage';
import { Layout } from '../app/Layout';
import { LoginPage } from '../features/auth/LoginPage';
import { ProjectCreatePage } from '../features/projects/ProjectCreatePage';
import { ProjectDashboardPage } from '../features/projects/ProjectDashboardPage';
import { DraftSubmissionPage } from '../features/submissions/DraftSubmissionPage';
import { ReviewQueuePage } from '../features/submissions/ReviewQueuePage';
import { WeeklyReportPage } from '../features/submissions/WeeklyReportPage';
import { ResourceListPage } from '../features/resources/ResourceListPage';
import { ProtectedRoute } from './ProtectedRoute';

function protectedPage(page: ReactElement) {
  return (
    <ProtectedRoute>
      <Layout>{page}</Layout>
    </ProtectedRoute>
  );
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <HomePage />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/projects/new',
    element: protectedPage(<ProjectCreatePage />),
  },
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
