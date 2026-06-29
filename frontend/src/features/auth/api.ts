import { apiRequest } from '../../shared/api/client';
import type { CurrentUser } from './AuthProvider';

export type LoginPayload = {
  email: string;
  password: string;
};

export function login(payload: LoginPayload): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/api/accounts/login/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function logout(): Promise<void> {
  return apiRequest<void>('/api/accounts/logout/', {
    method: 'POST',
  });
}

export function fetchCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/api/accounts/me/');
}
