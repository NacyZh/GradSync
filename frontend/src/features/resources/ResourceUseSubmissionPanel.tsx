import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, ClipboardList, Send, XCircle } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatUiDate, translateUiText } from '@/shared/i18n/translate';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import type { Booking, LaboratoryResource } from './api';
import {
  cancelBooking,
  createBooking,
  decideBooking,
  listBookings,
} from './api';

type ResourceUseSubmissionPanelProps = {
  resources: LaboratoryResource[];
  canManage: boolean;
};

export function ResourceUseSubmissionPanel({ resources, canManage }: ResourceUseSubmissionPanelProps) {
  const queryClient = useQueryClient();
  const { locale } = useI18n();
  const { notify } = useAppFeedback();
  const [resourceId, setResourceId] = useState(resources[0]?.id ? String(resources[0].id) : '');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [quantity, setQuantity] = useState('1');
  const bookingsQuery = useQuery({
    queryKey: canManage ? ['bookings', 'review-queue'] : ['bookings'],
    queryFn: () => listBookings(canManage ? { reviewQueue: true } : undefined),
  });
  const bookings = useMemo(() => (bookingsQuery.data?.results ?? [])
    .map((booking) => ({
      ...booking,
      resourceName: booking.resourceName ?? resources.find((resource) => resource.id === booking.resourceId)?.name ?? `Resource #${booking.resourceId}`,
    }))
    .sort((first, second) => getBookingSortTime(second) - getBookingSortTime(first)), [bookingsQuery.data, resources]);
  const pendingSubmissions = bookings.filter((booking) => booking.status === 'pending');
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

  function refreshResourceState() {
    void queryClient.invalidateQueries({ queryKey: ['bookings'] });
    void queryClient.invalidateQueries({ queryKey: ['resources'] });
    void queryClient.invalidateQueries({ queryKey: ['resource-availability'] });
  }

  const createMutation = useMutation({
    mutationFn: (payload: { resourceId: number; startsAt: string; endsAt: string; quantity: number; purpose?: string }) =>
      createBooking(payload),
    onSuccess: () => {
      notify(canManage ? 'Use recorded' : 'Use request pending review', 'success');
      refreshResourceState();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const decisionMutation = useMutation({
    mutationFn: (payload: { bookingId: number; approve: boolean; decisionNote?: string }) =>
      decideBooking(payload.bookingId, payload.approve, payload.decisionNote),
    onSuccess: () => {
      notify('Submission confirmed', 'success');
      refreshResourceState();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const cancelMutation = useMutation({
    mutationFn: cancelBooking,
    onSuccess: () => {
      notify('Request cancelled', 'success');
      refreshResourceState();
    },
    onError: (error) => notify(error.message, 'error'),
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const requestedQuantity = Number(form.get('quantity'));
    const startValue = String(form.get('startsAt') ?? '');
    const endValue = String(form.get('endsAt') ?? '');
    const startMs = new Date(startValue).getTime();
    const endMs = new Date(endValue).getTime();
    if (!selectedResource) {
      notify('Choose a resource before submitting.', 'error');
      return;
    }
    if (!Number.isInteger(requestedQuantity) || requestedQuantity < 1) {
      notify('Quantity must be a positive whole number.', 'error');
      return;
    }
    if (requestedQuantity > selectedResource.totalQuantity) {
      notify(`Quantity cannot exceed ${selectedResource.totalQuantity}.`, 'error');
      return;
    }
    if (!Number.isFinite(startMs) || (!canManage && startMs <= Date.now())) {
      notify('Student requests must start in the future.', 'error');
      return;
    }
    if (canManage && (!Number.isFinite(endMs) || endMs <= Date.now())) {
      notify('Direct use cannot be recorded after it has ended.', 'error');
      return;
    }
    if (!Number.isFinite(endMs) || endMs <= startMs) {
      notify('Use end time must be after start time.', 'error');
      return;
    }
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
          {selectedResource ? <small className="text-muted-foreground">{translateUiText(`Maximum ${selectedResource.totalQuantity} for ${selectedResource.name}`, locale)}</small> : null}
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="resourceUsePurpose">Purpose</Label>
          <Textarea id="resourceUsePurpose" name="purpose" placeholder="Briefly describe the intended use" />
        </div>
        <Button type="submit" disabled={createMutation.isPending || activeResources.length === 0}>
          <Send className="h-4 w-4" aria-hidden="true" />
          {canManage ? 'Record use' : 'Submit use request'}
        </Button>
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
        {bookingsQuery.isLoading ? <DataState state="loading" message="Loading resource use records." /> : null}
        {bookingsQuery.error ? <DataState state="error" title="Use records unavailable" message={bookingsQuery.error.message ?? 'Unable to load resource use records.'} /> : null}
        {!bookingsQuery.isLoading && !bookingsQuery.error && bookings.length === 0 ? <DataState state="empty" title={canManage ? 'No student requests' : 'No use submissions'} message={canManage ? 'Pending student resource requests appear here for review.' : 'Your resource use requests and direct outcomes appear here.'} /> : null}
        <ul className="resource-list max-h-[40.5rem] overflow-y-auto pr-1">
          {bookings.map((booking) => (
            <li key={`booking-${booking.id}`} className="min-h-24 items-start">
              <div className="min-w-0">
                <strong>{booking.resourceName}</strong>
                <p>{formatUiDate(booking.startsAt)} – {formatUiDate(booking.endsAt)} · {translateUiText(`Qty ${booking.quantity}`, locale)}</p>
                {canManage ? <p className="text-sm text-muted-foreground">{translateUiText(`${booking.requesterName ?? `Student #${booking.requestedById}`} · student request`, locale)}</p> : null}
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
        </ul>
      </section>
    </div>
  );
}

function getBookingSortTime(booking: Booking) {
  const candidates = [booking.createdAt, booking.startsAt, booking.endsAt];
  for (const value of candidates) {
    if (!value) continue;
    const time = new Date(value).getTime();
    if (Number.isFinite(time)) return time;
  }
  return 0;
}
