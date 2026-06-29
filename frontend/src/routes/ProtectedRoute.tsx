import type { PropsWithChildren } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthProvider';
import type { CurrentUser } from '../features/auth/AuthProvider';
import { AsyncState } from '../shared/ui/AsyncState';

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <AsyncState state="loading" message="Loading account" />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

type RoleGuardProps = PropsWithChildren<{
  allowedRoles: CurrentUser['global_role'][];
}>;

export function RoleRoute({ children, allowedRoles }: RoleGuardProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <AsyncState state="loading" message="Loading account" />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.global_role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
