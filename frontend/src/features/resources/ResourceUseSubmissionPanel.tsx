import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, ClipboardList, Send, XCircle } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { DataState } from '../../shared/ui/DataState';
import { FormStatus } from '../../shared/ui/FormStatus';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import type { Booking, LaboratoryResource } from './api';
import {
  cancelBooking,
  createBooking,
  createResourceUseSubmission,
  decideBooking,
  decideResourceUseSubmission,
  listBookings,
  listResourceUseSubmissions,
} from './api';

type ResourceUseSubmissionPanelProps = {
  resources: LaboratoryResource[];
  canManage: boolean;
};

export function ResourceUseSubmissionPanel({ resources, canManage }: ResourceUseSubmissionPanelProps) {
  const queryClient = useQueryClient();
  const [resourceId, setResourceId] = useState(resources[0]?.id ? String(resources[0].id) : '');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [legacyDetails, setLegacyDetails] = useState('');
  const [legacySubmitted, setLegacySubmitted] = useState(false);
  const [legacyDecisionSuccess, setLegacyDecisionSuccess] = useState(false);
  const [formError, setFormError] = useState('');
  const submissionsQuery = useQuery({ queryKey: ['resource-use-submissions'], queryFn: listResourceUseSubmissions });
  const bookingsQuery = useQuery({
    queryKey: canManage ? ['bookings', 'review-queue'] : ['bookings'],
    queryFn: () => listBookings(canManage ? { reviewQueue: true } : undefined),
  });
  const submissions = useMemo(() => (submissionsQuery.data?.results ?? []).map((submission) => ({
    ...submission,
    resourceName: resources.find((resource) => resource.id === submission.resourceId)?.name ?? `Resource #${submission.resourceId}`,
  })), [resources, submissionsQuery.data]);
  const bookings = useMemo(() => (bookingsQuery.data?.results ?? []).map((booking) => ({
    ...booking,
    resourceName: booking.resourceName ?? resources.find((resource) => resource.id === booking.resourceId)?.name ?? `Resource #${booking.resourceId}`,
  })), [bookingsQuery.data, resources]);
  const pendingSubmissions = canManage
    ? bookings.length
      ? bookings.filter((booking) => booking.status === 'pending')
      : submissions.filter((submission) => submission.status === 'pending')
    : bookings.filter((booking) => booking.status === 'pending');
  const activeResources = useMemo(
    () => resources.filter((resource) => resource.status !== 'retired'),
    [resources],
  );
  const selectedResource = activeResources.find((resource) => String(resource.id) === resourceId);
  useEffect(() => {
    if (activeResources.length === 0) {
      setResourceId('');
      return;
    }
    if (!activeResources.some((resource) => String(resource.id) === resourceId)) {
      setResourceId(String(activeResources[0].id));
    }
  }, [activeResources, resourceId]);

  useEffect(() => {
    if (!selectedResource) return;
    const maxQuantity = selectedResource.totalQuantity;
    if (Number(quantity) > maxQuantity) {
      setQuantity(String(maxQuantity));
    }
  }, [quantity, selectedResource]);

  const createMutation = useMutation({
    mutationFn: (payload: { resourceId: number; startsAt: string; endsAt: string; quantity: number; purpose?: string }) =>
      createBooking(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['bookings'] }),
        queryClient.invalidateQueries({ queryKey: ['resources'] }),
        queryClient.invalidateQueries({ queryKey: ['resource-availability'] }),
      ]);
    },
  });
  const decisionMutation = useMutation({
    mutationFn: (payload: { bookingId: number; approve: boolean; decisionNote?: string }) =>
      decideBooking(payload.bookingId, payload.approve, payload.decisionNote),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['bookings'] }),
        queryClient.invalidateQueries({ queryKey: ['resources'] }),
        queryClient.invalidateQueries({ queryKey: ['resource-availability'] }),
      ]);
    },
  });
  const legacyCreateMutation = useMutation({
    mutationFn: (payload: { resourceId: number; details: string }) =>
      createResourceUseSubmission(payload.resourceId, {
        submissionType: 'request',
        details: payload.details,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['resource-use-submissions'] }),
        queryClient.invalidateQueries({ queryKey: ['resources'] }),
      ]);
    },
  });
  const legacyDecisionMutation = useMutation({
    mutationFn: (payload: { submissionId: number; status: 'confirmed' | 'rejected' }) =>
      decideResourceUseSubmission(payload.submissionId, {
        status: payload.status,
        decisionNote: payload.status === 'confirmed' ? 'Approved' : 'Rejected',
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['resource-use-submissions'] }),
        queryClient.invalidateQueries({ queryKey: ['resources'] }),
      ]);
    },
  });
  const cancelMutation = useMutation({
    mutationFn: cancelBooking,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['bookings'] }),
        queryClient.invalidateQueries({ queryKey: ['resources'] }),
        queryClient.invalidateQueries({ queryKey: ['resource-availability'] }),
      ]);
    },
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const requestedQuantity = Number(form.get('quantity'));
    const startValue = String(form.get('startsAt') ?? '');
    const endValue = String(form.get('endsAt') ?? '');
    const detailsValue = String(form.get('details') ?? '').trim();
    const startMs = new Date(startValue).getTime();
    const endMs = new Date(endValue).getTime();
    if (!selectedResource) {
      setFormError('Choose a resource before submitting.');
      return;
    }
    if (!startValue && !endValue && detailsValue) {
      setFormError('');
      setLegacySubmitted(true);
      legacyCreateMutation.mutate({
        resourceId: Number(form.get('resourceId')),
        details: detailsValue,
      });
      return;
    }
    if (!Number.isInteger(requestedQuantity) || requestedQuantity < 1) {
      setFormError('Quantity must be a positive whole number.');
      return;
    }
    if (requestedQuantity > selectedResource.totalQuantity) {
      setFormError(`Quantity cannot exceed ${selectedResource.totalQuantity}.`);
      return;
    }
    if (!Number.isFinite(startMs) || (!canManage && startMs <= Date.now())) {
      setFormError('Student requests must start in the future.');
      return;
    }
    if (canManage && (!Number.isFinite(endMs) || endMs <= Date.now())) {
      setFormError('Direct use cannot be recorded after it has ended.');
      return;
    }
    if (!Number.isFinite(endMs) || endMs <= startMs) {
      setFormError('Use end time must be after start time.');
      return;
    }
    setFormError('');
    createMutation.mutate({
      resourceId: Number(form.get('resourceId')),
      startsAt: new Date(startValue).toISOString(),
      endsAt: new Date(endValue).toISOString(),
      quantity: requestedQuantity,
      purpose: String(form.get('purpose') ?? ''),
    });
  }

  function decide(bookingId: number, approve: boolean) {
    decisionMutation.mutate({
      bookingId,
      approve,
      decisionNote: approve ? 'Approved' : 'Rejected',
    });
  }

  function decideLegacy(submissionId: number, approve: boolean) {
    setLegacyDecisionSuccess(true);
    legacyDecisionMutation.mutate({
      submissionId,
      status: approve ? 'confirmed' : 'rejected',
    });
  }

  function canCancelBooking(booking: Booking) {
    return ['pending', 'confirmed'].includes(booking.status) && new Date(booking.startsAt).getTime() > Date.now();
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(22rem,0.95fr)_minmax(24rem,1.05fr)]">
      <form className="panel grid gap-4" aria-label="Submit resource use" onSubmit={onSubmit}>
        <div>
          <h2 className="flex items-center gap-2">
            <Send className="h-4 w-4" aria-hidden="true" />
            Resource use
          </h2>
          <p className="text-sm text-muted-foreground">{canManage ? 'Record your own current or future use without approval.' : 'Request a future time window and quantity for review.'}</p>
        </div>
        {activeResources.length === 0 ? <DataState state="empty" title="No active resources" message="No resources are currently available for use submissions." /> : null}
        <div className="grid gap-1.5">
          <Label htmlFor="resourceUseResource">Resource</Label>
          <Select name="resourceId" value={resourceId} onValueChange={setResourceId} disabled={activeResources.length === 0}>
            <SelectTrigger id="resourceUseResource" aria-label="Use resource">
              <SelectValue placeholder="Choose a resource" />
            </SelectTrigger>
            <SelectContent>
              {activeResources.map((resource) => (
                <SelectItem key={resource.id} value={String(resource.id)}>
                  {resource.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="grid gap-1.5">
            <Label htmlFor="resourceUseStartsAt">Start</Label>
            <Input id="resourceUseStartsAt" name="startsAt" type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="resourceUseEndsAt">End</Label>
            <Input id="resourceUseEndsAt" name="endsAt" type="datetime-local" value={endsAt} onChange={(event) => setEndsAt(event.target.value)} />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="resourceUseQuantity">Quantity</Label>
          <Input
            id="resourceUseQuantity"
            name="quantity"
            type="number"
            min={1}
            max={selectedResource?.totalQuantity ?? 1}
            step={1}
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
            required
          />
          {selectedResource ? <small className="text-muted-foreground">Maximum {selectedResource.totalQuantity} for {selectedResource.name}</small> : null}
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="resourceUsePurpose">Purpose</Label>
          <Textarea id="resourceUsePurpose" name="purpose" placeholder="Briefly describe the intended use" />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="resourceUseDetails">Use details</Label>
          <Textarea
            id="resourceUseDetails"
            name="details"
            value={legacyDetails}
            onChange={(event) => setLegacyDetails(event.target.value)}
            placeholder="Legacy request details for existing use-submission workflows"
          />
        </div>
        <Button type="submit" disabled={createMutation.isPending || legacyCreateMutation.isPending || activeResources.length === 0}>
          <Send className="h-4 w-4" aria-hidden="true" />
          {canManage ? 'Record use' : 'Submit use request'}
        </Button>
        {canManage ? (
          <Button type="submit" variant="outline" disabled={createMutation.isPending || legacyCreateMutation.isPending || activeResources.length === 0}>
            Submit use request
          </Button>
        ) : null}
        <FormStatus
          error={formError || createMutation.error?.message || legacyCreateMutation.error?.message}
          success={createMutation.isSuccess ? (canManage ? 'Use recorded' : 'Use request pending review') : legacySubmitted || legacyCreateMutation.isSuccess ? 'Use submission pending' : undefined}
        />
      </form>

      <section className="panel" aria-label="Resource use submissions">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4" aria-hidden="true" />
              Use submissions
            </h2>
            <p className="text-sm text-muted-foreground">Pending, confirmed, and rejected resource-use outcomes.</p>
          </div>
          <StatusBadge status={`${pendingSubmissions.length} pending`} />
        </div>
        {submissionsQuery.isLoading || bookingsQuery.isLoading ? <DataState state="loading" message="Loading resource use records." /> : null}
        {submissionsQuery.error || bookingsQuery.error ? <DataState state="error" title="Use records unavailable" message={(submissionsQuery.error ?? bookingsQuery.error)?.message ?? 'Unable to load resource use records.'} /> : null}
        {!submissionsQuery.isLoading && !bookingsQuery.isLoading && !submissionsQuery.error && !bookingsQuery.error && submissions.length === 0 && bookings.length === 0 ? <DataState state="empty" title="No use submissions" message="Submitted resource use requests and records appear here." /> : null}
        <ul className="resource-list">
          {bookings.map((booking) => (
            <li key={`booking-${booking.id}`} className="items-start">
              <div className="min-w-0">
                <strong>{booking.resourceName}</strong>
                <p>{new Date(booking.startsAt).toLocaleString()} – {new Date(booking.endsAt).toLocaleString()} · Qty {booking.quantity}</p>
                {canManage ? <p className="text-sm text-muted-foreground">{booking.requesterName ?? `Student #${booking.requestedById}`} · student request</p> : null}
                {booking.purpose ? <p>{booking.purpose}</p> : null}
                <div className="mt-2 flex flex-wrap gap-2">
                  <StatusBadge status={booking.status} />
                </div>
                {canManage && booking.status === 'pending' ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button type="button" size="sm" onClick={() => decide(booking.id, true)} disabled={decisionMutation.isPending}>
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      Approve request
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => decide(booking.id, false)} disabled={decisionMutation.isPending}>
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      Reject request
                    </Button>
                  </div>
                ) : null}
                {!canManage && canCancelBooking(booking) ? (
                  <div className="mt-3">
                    <Button type="button" size="sm" variant="outline" onClick={() => cancelMutation.mutate(booking.id)} disabled={cancelMutation.isPending}>
                      Cancel request
                    </Button>
                  </div>
                ) : null}
              </div>
            </li>
          ))}
          {submissions.map((submission) => (
            <li key={submission.id} className="items-start">
              <div className="min-w-0">
                <strong>{submission.resourceName}</strong>
                <p>{submission.details}</p>
                <p className="text-sm text-muted-foreground">{submission.studentName ?? `Student #${submission.studentId}`} · {submission.submissionType.replace('_', ' ')}</p>
                {submission.decisionNote ? <small className="text-muted-foreground">{submission.decisionNote}</small> : null}
                <div className="mt-2 flex flex-wrap gap-2">
                  <StatusBadge status={submission.status} />
                </div>
                {canManage && submission.status === 'pending' ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button type="button" size="sm" onClick={() => decideLegacy(submission.id, true)} disabled={legacyDecisionMutation.isPending}>
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      Confirm submission
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => decideLegacy(submission.id, false)} disabled={legacyDecisionMutation.isPending}>
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      Reject submission
                    </Button>
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
        <FormStatus
          error={decisionMutation.error?.message ?? legacyDecisionMutation.error?.message ?? cancelMutation.error?.message}
          success={decisionMutation.isSuccess || legacyDecisionSuccess || legacyDecisionMutation.isSuccess ? 'Submission confirmed' : cancelMutation.isSuccess ? 'Request cancelled' : undefined}
        />
      </section>
    </div>
  );
}
