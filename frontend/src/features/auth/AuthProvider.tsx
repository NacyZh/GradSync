import { createContext, useContext, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { login as loginApi, logout as logoutApi, fetchCurrentUser } from './api';
import { clearAccessToken, restoreAccessToken } from '../../shared/auth/tokenStore';

export type CurrentUser = {
  id: number;
  email: string;
  name: string;
  nickname?: string;
  global_role: 'advisor' | 'student' | 'admin';
  requested_role?: 'student' | 'teacher' | 'administrator' | 'pending';
  active_role?: 'student' | 'teacher' | 'administrator' | 'pending';
  status: 'active' | 'suspended' | 'archived' | 'invited' | 'pending_email_verification' | 'pending_role_activation';
  degreeType?: 'masters' | 'doctoral' | null;
};

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<CurrentUser>;
  logout: () => Promise<void>;
  isLoggingIn: boolean;
  isLoggingOut: boolean;
  loginError: string | null;
};

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  login: async () => {
    throw new Error('AuthProvider not mounted');
  },
  logout: async () => {},
  isLoggingIn: false,
  isLoggingOut: false,
  loginError: null,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      await restoreAccessToken();
      return fetchCurrentUser();
    },
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      loginApi({ email, password }),
    onSuccess: (user) => {
      queryClient.setQueryData(['current-user'], user);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: logoutApi,
    onSuccess: () => {
      queryClient.setQueryData(['current-user'], null);
      queryClient.clear();
    },
  });

  const login = useCallback(
    async (email: string, password: string) => {
      return loginMutation.mutateAsync({ email, password });
    },
    [loginMutation],
  );

  const logout = useCallback(async () => {
    await logoutMutation.mutateAsync();
  }, [logoutMutation]);

  useEffect(() => {
    function handleAuthRequired() {
      clearAccessToken();
      queryClient.setQueryData(['current-user'], null);
    }
    window.addEventListener('gradsync:auth-required', handleAuthRequired);
    return () => window.removeEventListener('gradsync:auth-required', handleAuthRequired);
  }, [queryClient]);

  return (
    <AuthContext.Provider
      value={{
        user: data ?? null,
        isLoading,
        login,
        logout,
        isLoggingIn: loginMutation.isPending,
        isLoggingOut: logoutMutation.isPending,
        loginError: loginMutation.error?.message ?? null,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
