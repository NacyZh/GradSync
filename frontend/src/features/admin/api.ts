import { apiRequest } from '../../shared/api/client';
import type { CurrentUser } from '../auth/AuthProvider';

export type PaginatedAccounts = {
  count: number;
  next: string | null;
  previous: string | null;
  results: CurrentUser[];
};

export function listAccounts(pageUrl?: string): Promise<PaginatedAccounts> {
  const path = pageUrl ?? '/api/accounts/admin/';
  return apiRequest<PaginatedAccounts>(path);
}

export function createAccount(payload: {
  email: string;
  name: string;
  global_role: 'advisor' | 'student';
}): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/api/accounts/admin/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateAccount(
  id: number,
  payload: { name?: string; global_role?: string },
): Promise<CurrentUser> {
  return apiRequest<CurrentUser>(`/api/accounts/admin/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function accountAction(
  id: number,
  action: 'suspend' | 'reactivate' | 'archive',
): Promise<CurrentUser> {
  return apiRequest<CurrentUser>(`/api/accounts/admin/${id}/`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

export type RoleActivation = {
  id: number;
  user: CurrentUser;
  requestedRole: 'teacher' | 'administrator';
  activationSource: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'revoked';
  createdAt: string;
  reviewedAt?: string | null;
};

export function listRoleActivations(): Promise<RoleActivation[]> {
  return apiRequest<RoleActivation[]>('/api/accounts/admin/role-activations/');
}

export function decideRoleActivation(id: number, action: 'approve' | 'reject' | 'revoke' | 'expire') {
  return apiRequest<RoleActivation>(`/api/accounts/admin/role-activations/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ action }),
  });
}
