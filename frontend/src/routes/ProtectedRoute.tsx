import type { PropsWithChildren } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthProvider';
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
