import { createContext, useContext } from 'react';
import { useQuery } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';

export type CurrentUser = {
  id: number;
  email: string;
  name: string;
  global_role: 'advisor' | 'student' | 'admin';
  status: 'active' | 'suspended' | 'archived';
};

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
};

const AuthContext = createContext<AuthContextValue>({ user: null, isLoading: true });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useQuery({
    queryKey: ['current-user'],
    queryFn: () => apiRequest<CurrentUser>('/api/accounts/me/'),
    retry: false,
  });

  return <AuthContext.Provider value={{ user: data ?? null, isLoading }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
