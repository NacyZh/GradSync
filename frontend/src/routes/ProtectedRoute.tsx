import type { PropsWithChildren } from 'react';

import { useAuth } from '../features/auth/AuthProvider';
import { AsyncState } from '../shared/ui/AsyncState';

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <AsyncState state="loading" message="Loading account" />;
  }

  if (!user) {
    return <AsyncState state="empty" message="Sign in to continue" />;
  }

  return <>{children}</>;
}
