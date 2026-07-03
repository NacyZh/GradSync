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

export type LaboratoryResource = {
  id: number;
  name: string;
  resourceType: string;
  description?: string;
  status: 'active' | 'unavailable' | 'retired';
  managerId?: number | null;
  useInstructions?: string;
  useSubmissions?: ResourceUseSubmission[];
};

export function listResourceTypes() {
  return apiRequest<{ results: ResourceType[] }>('/api/resource-types/');
}

export function listResources() {
  return apiRequest<{ results: ResourceItem[] }>('/api/resource-items/');
}

export function listLaboratoryResources() {
  return apiRequest<{ results: LaboratoryResource[] }>('/api/resources/');
}

export function createLaboratoryResource(payload: { name: string; resourceType: string; description?: string; useInstructions?: string }) {
  return apiRequest<LaboratoryResource>('/api/resources/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateLaboratoryResource(resourceId: number, payload: Partial<Pick<LaboratoryResource, 'name' | 'resourceType' | 'description' | 'status' | 'useInstructions'>>) {
  return apiRequest<LaboratoryResource>(`/api/resources/${resourceId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function retireLaboratoryResource(resourceId: number) {
  return apiRequest<void>(`/api/resources/${resourceId}/`, { method: 'DELETE' });
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
