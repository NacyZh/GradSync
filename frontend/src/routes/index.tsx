import { lazy, Suspense, type ReactElement } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

import { HomePage } from '../app/HomePage';
import { Layout } from '../app/Layout';
import { LoginPage } from '../features/auth/LoginPage';
import { RegisterPage } from '../features/auth/RegisterPage';
import { DataState } from '../shared/ui/DataState';
import { ProtectedRoute, RoleRoute } from './ProtectedRoute';

export const routeWorkspaceBundles = {
  accountAdmin: () => import('../features/admin/AccountAdminPage'),
  roleActivation: () => import('../features/admin/RoleActivationPage'),
  profile: () => import('../features/auth/ProfilePage'),
  projectCreate: () => import('../features/projects/ProjectCreatePage'),
  projectDashboard: () => import('../features/projects/ProjectDashboardPage'),
  projectMaterials: () => import('../features/projects/ProjectMaterialsPage'),
  draftSubmission: () => import('../features/submissions/DraftSubmissionPage'),
  weeklyReport: () => import('../features/submissions/WeeklyReportPage'),
  reviewQueue: () => import('../features/submissions/ReviewQueuePage'),
  writingProjects: () => import('../features/submissions/WritingProjectsPage'),
  resources: () => import('../features/resources/ResourceListPage'),
  paperLibrary: () => import('../features/library/PaperLibraryPage'),
  documentLibrary: () => import('../features/library/DocumentLibraryPage'),
  codeRepository: () => import('../features/repositories/CodeRepositoryPage'),
} as const;

const AccountAdminPage = lazy(async () => ({ default: (await routeWorkspaceBundles.accountAdmin()).AccountAdminPage }));
const RoleActivationPage = lazy(async () => ({ default: (await routeWorkspaceBundles.roleActivation()).RoleActivationPage }));
const ProfilePage = lazy(async () => ({ default: (await routeWorkspaceBundles.profile()).ProfilePage }));
const ProjectCreatePage = lazy(async () => ({ default: (await routeWorkspaceBundles.projectCreate()).ProjectCreatePage }));
const ProjectDashboardPage = lazy(async () => ({ default: (await routeWorkspaceBundles.projectDashboard()).ProjectDashboardPage }));
const ProjectMaterialsPage = lazy(async () => ({ default: (await routeWorkspaceBundles.projectMaterials()).ProjectMaterialsPage }));
const DraftSubmissionPage = lazy(async () => ({ default: (await routeWorkspaceBundles.draftSubmission()).DraftSubmissionPage }));
const WeeklyReportPage = lazy(async () => ({ default: (await routeWorkspaceBundles.weeklyReport()).WeeklyReportPage }));
const ReviewQueuePage = lazy(async () => ({ default: (await routeWorkspaceBundles.reviewQueue()).ReviewQueuePage }));
const WritingProjectsPage = lazy(async () => ({ default: (await routeWorkspaceBundles.writingProjects()).WritingProjectsPage }));
const ResourceListPage = lazy(async () => ({ default: (await routeWorkspaceBundles.resources()).ResourceListPage }));
const PaperLibraryPage = lazy(async () => ({ default: (await routeWorkspaceBundles.paperLibrary()).PaperLibraryPage }));
const DocumentLibraryPage = lazy(async () => ({ default: (await routeWorkspaceBundles.documentLibrary()).DocumentLibraryPage }));
const CodeRepositoryPage = lazy(async () => ({ default: (await routeWorkspaceBundles.codeRepository()).CodeRepositoryPage }));

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
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/profile',
    element: protectedPage(<ProfilePage />),
  },
  // Admin-only: account management.
  {
    path: '/admin/accounts',
    element: rolePage(<AccountAdminPage />, 'admin'),
  },
  {
    path: '/admin/role-activations',
    element: rolePage(<RoleActivationPage />, 'admin'),
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
    path: '/projects/:projectId/materials',
    element: protectedPage(<ProjectMaterialsPage />),
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
    path: '/writing',
    element: protectedPage(<WritingProjectsPage />),
  },
  {
    path: '/projects/:projectId/writing',
    element: protectedPage(<Navigate to="/writing" replace />),
  },
  {
    path: '/projects/:projectId/resources',
    element: protectedPage(<Navigate to="/resources" replace />),
  },
  {
    path: '/projects/:projectId/papers',
    element: protectedPage(<Navigate to="/library/papers" replace />),
  },
  {
    path: '/library/papers',
    element: protectedPage(<PaperLibraryPage />),
  },
  {
    path: '/library/documents',
    element: protectedPage(<DocumentLibraryPage />),
  },
  {
    path: '/library/code',
    element: protectedPage(<CodeRepositoryPage />),
  },
  {
    path: '/projects/:projectId/documents',
    element: protectedPage(<Navigate to="/library/documents" replace />),
  },
  {
    path: '/projects/:projectId/code',
    element: protectedPage(<Navigate to="/library/code" replace />),
  },
  {
    path: '/resources',
    element: protectedPage(<ResourceListPage />),
  },
]);
