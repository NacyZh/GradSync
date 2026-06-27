import { apiRequest } from '../../shared/api/client';

export type LabResource = {
  id: number;
  name: string;
  resource_type: string;
  location?: string;
  status: string;
  available?: boolean;
  conflicting_booking_count?: number;
};

export type Booking = {
  id: number;
  project_id: number;
  resource_id: number;
  starts_at: string;
  ends_at: string;
  status: string;
  purpose?: string;
};

export function listResources() {
  return apiRequest<{ results: LabResource[] }>('/api/resources/');
}

export function listResourceAvailability(startsAt: string, endsAt: string) {
  const params = new URLSearchParams({
    starts_at: new Date(startsAt).toISOString(),
    ends_at: new Date(endsAt).toISOString(),
  });
  return apiRequest<LabResource[]>(`/api/resources/availability/?${params.toString()}`);
}

export function listBookings(projectId: number) {
  return apiRequest<{ results: Booking[] }>(`/api/projects/${projectId}/bookings/`);
}

export function createBooking(projectId: number, payload: { resource_id: number; starts_at: string; ends_at: string; purpose?: string }) {
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
