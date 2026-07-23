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
  reviewer?: CurrentUser | null;
  reviewReason?: string;
};

export type PaginatedRoleActivations = {
  count: number;
  next: string | null;
  previous: string | null;
  results: RoleActivation[];
};

export function listRoleActivations({
  status = 'pending',
  query = '',
  pageUrl,
}: {
  status?: 'pending' | 'processed';
  query?: string;
  pageUrl?: string;
} = {}): Promise<PaginatedRoleActivations> {
  if (pageUrl) return apiRequest<PaginatedRoleActivations>(pageUrl);
  const params = new URLSearchParams({ status });
  if (query.trim()) params.set('q', query.trim());
  return apiRequest<PaginatedRoleActivations>(
    `/api/accounts/admin/role-activations/?${params.toString()}`,
  );
}

export function decideRoleActivation(
  id: number,
  action: 'approve' | 'reject' | 'revoke',
  reason = '',
) {
  return apiRequest<RoleActivation>(`/api/accounts/admin/role-activations/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ action, reason }),
  });
}
