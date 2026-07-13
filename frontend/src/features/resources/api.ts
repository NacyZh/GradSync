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
  resourceType?: string;
  totalQuantity: number;
  availableQuantity?: number;
  confirmationPolicyOverride?: ConfirmationPolicy | null;
  effectiveConfirmationPolicy: ConfirmationPolicy;
  version: number;
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
  requestedById: number;
  startsAt: string;
  endsAt: string;
  quantity: number;
  confirmationPolicy: ConfirmationPolicy;
  status: string;
  purpose?: string;
  reviewerId?: number | null;
  decisionNote?: string;
  version: number;
};

export type ResourceUseSubmission = {
  id: number;
  resourceId: number;
  studentId: number;
  studentName?: string;
  submissionType: 'request' | 'use_record';
  details: string;
  status: 'pending' | 'confirmed' | 'rejected';
  reviewerId?: number | null;
  decisionNote?: string;
  submitted_at?: string;
  decided_at?: string | null;
};

function isResourceUseSubmission(value: unknown): value is ResourceUseSubmission {
  if (!value || typeof value !== 'object') return false;
  const item = value as Record<string, unknown>;
  return typeof item.id === 'number'
    && typeof item.resourceId === 'number'
    && typeof item.studentId === 'number'
    && (item.studentName === undefined || typeof item.studentName === 'string')
    && (item.submissionType === 'request' || item.submissionType === 'use_record')
    && typeof item.details === 'string'
    && (item.status === 'pending' || item.status === 'confirmed' || item.status === 'rejected');
}

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
  useSubmissions?: ResourceUseSubmission[];
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

export function createResourceUseSubmission(resourceId: number, payload: { submissionType: ResourceUseSubmission['submissionType']; details: string }) {
  return apiRequest<ResourceUseSubmission>(`/api/resources/${resourceId}/use-submissions/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function decideResourceUseSubmission(submissionId: number, payload: { status: 'confirmed' | 'rejected'; decisionNote?: string }) {
  return apiRequest<ResourceUseSubmission>(`/api/resource-use-submissions/${submissionId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function listResourceAvailability(startsAt: string, endsAt: string) {
  const params = new URLSearchParams({
    startsAt: new Date(startsAt).toISOString(),
    endsAt: new Date(endsAt).toISOString(),
  });
  return apiRequest<ResourceItem[] | { results: ResourceItem[] }>(`/api/resources/availability/?${params.toString()}`)
    .then((response) => Array.isArray(response) ? response : response.results);
}

export function listBookings() {
  return apiRequest<{ results: Booking[] }>('/api/bookings/');
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

export function listResourceUseSubmissions() {
  return apiRequest<{ results: unknown[] }>('/api/resource-use-submissions/')
    .then((page) => {
      if (!page || !Array.isArray(page.results) || !page.results.every(isResourceUseSubmission)) {
        throw new Error('Resource use records do not match the current API contract.');
      }
      return { ...page, results: page.results };
    });
}
