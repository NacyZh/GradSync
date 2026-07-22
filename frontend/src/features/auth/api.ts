import { apiRequest } from '../../shared/api/client';
import { clearAccessToken, setAccessToken } from '../../shared/auth/tokenStore';
import type { CurrentUser } from './AuthProvider';

export type LoginPayload = {
  email: string;
  password: string;
};

type LoginResponse = CurrentUser & { accessToken?: string; accessTokenExpiresAt?: string };

export async function login(payload: LoginPayload): Promise<CurrentUser> {
  const response = await apiRequest<LoginResponse>('/api/accounts/login/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  setAccessToken(response);
  return response;
}

export async function logout(): Promise<void> {
  try {
    await apiRequest<void>('/api/accounts/logout/', { method: 'POST' });
  } finally {
    clearAccessToken();
  }
}

export function fetchCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/api/accounts/me/');
}

export type RegisterPayload = {
  email: string;
  password: string;
  name: string;
  nickname: string;
  requestedRole: 'student' | 'teacher';
  degreeType?: 'masters' | 'doctoral' | '';
};

export function register(payload: RegisterPayload): Promise<{ email: string; status: string; requestedRole: string }> {
  return apiRequest('/api/accounts/register/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function verifyEmail(payload: { email: string; code: string }): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/api/accounts/verify-email/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function resendVerification(email: string): Promise<{ message: string }> {
  return apiRequest('/api/accounts/resend-verification/', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function updateProfile(payload: {
  name: string;
  nickname: string;
  degreeType?: 'masters' | 'doctoral' | null;
}): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/api/accounts/me/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function changePassword(payload: { currentPassword: string; newPassword: string }): Promise<void> {
  return apiRequest<void>('/api/accounts/me/password/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
