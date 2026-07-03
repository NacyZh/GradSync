import { apiRequest } from '../../shared/api/client';

export type ResourceItem = {
  id: number;
  resourceTypeId: number;
  name: string;
  description?: string;
  location?: string;
  fieldValues?: Record<string, unknown>;
  availabilityPolicy?: Record<string, unknown>;
  status: string;
  available?: boolean;
  conflictingBookingCount?: number;
};

export type ResourceType = {
  id: number;
  name: string;
  description?: string;
  scope: 'global' | 'project';
  fieldSchema: Array<{ key: string; label: string; fieldType: string; required: boolean; options?: string[] }>;
  eligibilityPolicy?: Record<string, unknown>;
  bookingPolicy?: Record<string, unknown>;
  status: string;
};

export type Booking = {
  id: number;
  project_id: number;
  resourceItemId: number;
  starts_at: string;
  ends_at: string;
  status: string;
  purpose?: string;
};

export function listResourceTypes() {
  return apiRequest<{ results: ResourceType[] }>('/api/resource-types/');
}

export function listResources() {
  return apiRequest<{ results: ResourceItem[] }>('/api/resource-items/');
}

export function listResourceAvailability(startsAt: string, endsAt: string) {
  const params = new URLSearchParams({
    starts_at: new Date(startsAt).toISOString(),
    ends_at: new Date(endsAt).toISOString(),
  });
  return apiRequest<ResourceItem[]>(`/api/resource-items/availability/?${params.toString()}`);
}

export function listBookings(projectId: number) {
  return apiRequest<{ results: Booking[] }>(`/api/projects/${projectId}/bookings/`);
}

export function createBooking(projectId: number, payload: { resourceItemId: number; starts_at: string; ends_at: string; purpose?: string }) {
  return apiRequest<Booking>(`/api/projects/${projectId}/bookings/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateBooking(projectId: number, bookingId: number, payload: Partial<Booking>) {
  return apiRequest<Booking>(`/api/projects/${projectId}/bookings/${bookingId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function cancelBooking(projectId: number, bookingId: number) {
  return apiRequest<Booking>(`/api/projects/${projectId}/bookings/${bookingId}/cancel/`, { method: 'POST' });
}
