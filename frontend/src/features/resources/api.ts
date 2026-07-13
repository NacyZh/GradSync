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
  allocatedQuantity?: number;
  resourceType?: string;
  totalQuantity: number;
  availableQuantity?: number;
  confirmationPolicyOverride?: ConfirmationPolicy | null;
  effectiveConfirmationPolicy: ConfirmationPolicy;
  version: number;
  currentUsePeriods?: Array<{ bookingId: number; startsAt: string; endsAt: string; quantity: number }>;
};

export type ResourceAvailabilityResponse = {
  observedAt?: string;
  freshnessToken?: string;
  results: ResourceItem[];
};

export type ConfirmationPolicy = 'immediate' | 'approval_required';

export type ResourceType = {
  id: number;
  name: string;
  description?: string;
  scope: 'global' | 'project';
  fieldSchema: Array<{ key: string; label: string; fieldType: string; required: boolean; options?: string[] }>;
  eligibilityPolicy?: Record<string, unknown>;
  bookingPolicy?: Record<string, unknown>;
  confirmationPolicy: ConfirmationPolicy;
  status: string;
};

export type Booking = {
  id: number;
  resourceId: number;
  resourceName?: string;
  requestedById: number;
  requesterName?: string;
  startsAt: string;
  endsAt: string;
  quantity: number;
  origin: 'student_request' | 'staff_direct' | 'legacy_booking';
  confirmationPolicy: ConfirmationPolicy;
  status: string;
  purpose?: string;
  reviewerId?: number | null;
  decisionNote?: string;
  completedAt?: string | null;
  cancelledAt?: string | null;
  createdAt?: string;
  version: number;
};

export type LaboratoryResource = {
  id: number;
  name: string;
  resourceType: string;
  resourceTypeId: number;
  description?: string;
  location?: string;
  totalQuantity: number;
  availableQuantity: number;
  status: 'active' | 'unavailable' | 'retired';
  managerId?: number | null;
  useInstructions?: string;
  confirmationPolicyOverride?: ConfirmationPolicy | null;
  effectiveConfirmationPolicy: ConfirmationPolicy;
  version: number;
  currentUsePeriods?: Array<{ bookingId: number; startsAt: string; endsAt: string; quantity: number }>;
};

export type ResourceWrite = {
  name: string;
  resourceType: string;
  totalQuantity: number;
  location?: string;
  description?: string;
  status?: LaboratoryResource['status'];
  useInstructions?: string;
  confirmationPolicyOverride?: ConfirmationPolicy | null;
};

export function listResourceTypes() {
  return apiRequest<{ results: ResourceType[] }>('/api/resource-types/');
}

export function listResources() {
  return apiRequest<{ results: LaboratoryResource[] }>('/api/resources/');
}

export function listLaboratoryResources() {
  return apiRequest<{ results: LaboratoryResource[] }>('/api/resources/');
}

export function createLaboratoryResource(payload: ResourceWrite) {
  return apiRequest<LaboratoryResource>('/api/resources/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateLaboratoryResource(resourceId: number, payload: Partial<ResourceWrite> & { version: number }) {
  return apiRequest<LaboratoryResource>(`/api/resources/${resourceId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteLaboratoryResource(resourceId: number) {
  return apiRequest<void>(`/api/resources/${resourceId}/`, { method: 'DELETE' });
}

export function retireLaboratoryResource(resourceId: number, version: number) {
  return apiRequest<LaboratoryResource>(`/api/resources/${resourceId}/retire/`, {
    method: 'POST',
    body: JSON.stringify({ version }),
  });
}

export function listResourceAvailability(startsAt: string, endsAt: string) {
  const params = new URLSearchParams({
    startsAt: new Date(startsAt).toISOString(),
    endsAt: new Date(endsAt).toISOString(),
  });
  return apiRequest<ResourceItem[] | ResourceAvailabilityResponse>(`/api/resources/availability/?${params.toString()}`)
    .then((response) => Array.isArray(response) ? { results: response } : response);
}

export function listBookings(params?: { reviewQueue?: boolean; origin?: Booking['origin']; status?: string }) {
  const search = new URLSearchParams();
  if (params?.reviewQueue) search.set('reviewQueue', 'true');
  if (params?.origin) search.set('origin', params.origin);
  if (params?.status) search.set('status', params.status);
  const suffix = search.toString() ? `?${search.toString()}` : '';
  return apiRequest<{ results: Booking[] }>(`/api/bookings/${suffix}`);
}

export function createBooking(payload: { resourceId: number; startsAt: string; endsAt: string; quantity: number; purpose?: string }) {
  return apiRequest<Booking>('/api/bookings/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateBooking(bookingId: number, payload: Partial<Booking>) {
  return apiRequest<Booking>(`/api/bookings/${bookingId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function cancelBooking(bookingId: number) {
  return apiRequest<Booking>(`/api/bookings/${bookingId}/cancel/`, { method: 'POST' });
}

export function decideBooking(bookingId: number, approve: boolean, decisionNote = '') {
  return apiRequest<Booking>(`/api/bookings/${bookingId}/${approve ? 'approve' : 'reject'}/`, {
    method: 'POST', body: JSON.stringify({ decisionNote }),
  });
}
