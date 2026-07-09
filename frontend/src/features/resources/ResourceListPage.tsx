import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { CalendarDays, PlusCircle, Search, SlidersHorizontal, Wrench } from 'lucide-react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { useAuth } from '../auth/AuthProvider';
import { DataState } from '../../shared/ui/DataState';
import { FormStatus } from '../../shared/ui/FormStatus';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { NotificationList } from '../notifications/NotificationList';
import { BookingActions } from './BookingActions';
import { BookingCalendar } from './BookingCalendar';
import { BookingForm } from './BookingForm';
import type { Booking, LaboratoryResource, ResourceItem, ResourceType } from './api';
import { createLaboratoryResource, listBookings, listLaboratoryResources, listResources, listResourceTypes } from './api';
import { ResourceUseSubmissionPanel } from './ResourceUseSubmissionPanel';

export function ResourceListPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManageResources = user?.global_role === 'advisor' || user?.global_role === 'admin';
  const [query, setQuery] = useState('');
  const [resourceType, setResourceType] = useState('all');
  const [resourceStatus, setResourceStatus] = useState('bookable');
  const [availabilityWindow, setAvailabilityWindow] = useState({ startsAt: '', endsAt: '', hasValidWindow: true });
  const resourceTypesQuery = useQuery({ queryKey: ['resource-types'], queryFn: listResourceTypes });
  const resourcesQuery = useQuery({ queryKey: ['resources'], queryFn: listResources });
  const laboratoryResourcesQuery = useQuery({ queryKey: ['laboratory-resources'], queryFn: listLaboratoryResources });
  const bookingsQuery = useQuery({ queryKey: ['bookings', projectId], queryFn: () => listBookings(projectId), enabled: Boolean(projectId) });
  const resources = useMemo(() => resourcesQuery.data?.results ?? [], [resourcesQuery.data?.results]);
  const laboratoryResources = useMemo(() => laboratoryResourcesQuery.data?.results ?? [], [laboratoryResourcesQuery.data?.results]);
  const resourceTypes = useMemo(() => resourceTypesQuery.data?.results ?? [], [resourceTypesQuery.data?.results]);
  const bookings = useMemo(() => bookingsQuery.data?.results ?? [], [bookingsQuery.data?.results]);
  const resourceById = useMemo(() => new Map(resources.map((resource) => [resource.id, resource])), [resources]);
  const resourceTypeById = useMemo(() => new Map(resourceTypes.map((type) => [type.id, type])), [resourceTypes]);
  const filteredResources = useMemo(
    () => resources.filter((resource) => {
      const typeName = resourceTypeById.get(resource.resourceTypeId)?.name ?? '';
      const searchable = `${resource.name} ${typeName} ${resource.location ?? ''}`.toLowerCase();
      const matchesQuery = searchable.includes(query.toLowerCase());
      const matchesType = resourceType === 'all' || String(resource.resourceTypeId) === resourceType;
      const matchesStatus = resourceStatus === 'all'
        || (resourceStatus === 'bookable' ? resource.status !== 'retired' && resource.status !== 'unavailable' : resource.status === resourceStatus);
      return matchesQuery && matchesType && matchesStatus;
    }),
    [query, resourceStatus, resourceType, resourceTypeById, resources],
  );
  const upcomingBookings = useMemo(() => {
    const now = Date.now();
    return bookings
      .filter((booking) => booking.status !== 'cancelled')
      .sort((left, right) => new Date(left.starts_at).getTime() - new Date(right.starts_at).getTime())
      .filter((booking) => new Date(booking.ends_at).getTime() >= now);
  }, [bookings]);
  const startedBookings = upcomingBookings.filter((booking) => new Date(booking.starts_at).getTime() <= Date.now());
  const activeFilterCount = [query ? 'query' : '', resourceType !== 'all' ? resourceType : '', resourceStatus !== 'bookable' ? resourceStatus : ''].filter(Boolean).length;
  const createResourceMutation = useMutation({
    mutationFn: createLaboratoryResource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['laboratory-resources'] }),
  });
  const filteredLaboratoryResources = useMemo(
    () => laboratoryResources.filter((resource) => {
      const searchable = `${resource.name} ${resource.resourceType} ${resource.description ?? ''}`.toLowerCase();
      const matchesQuery = searchable.includes(query.toLowerCase());
      const matchesType = resourceType === 'all' || resource.resourceType === resourceType;
      const matchesStatus = resourceStatus === 'all'
        || (resourceStatus === 'bookable' ? resource.status !== 'retired' && resource.status !== 'unavailable' : resource.status === resourceStatus);
      return matchesQuery && matchesType && matchesStatus;
    }),
    [laboratoryResources, query, resourceStatus, resourceType],
  );
  const laboratoryResourceTypes = Array.from(new Set(laboratoryResources.map((resource) => resource.resourceType))).sort();

  function onCreateResource(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    createResourceMutation.mutate({
      name: String(form.get('name') ?? ''),
      resourceType: String(form.get('resourceType') ?? ''),
      description: String(form.get('description') ?? ''),
      useInstructions: String(form.get('useInstructions') ?? ''),
    });
  }

  return (
    <PageShell
      title="Lab resources"
      description="Search configurable resource items, reserve eligible resources, and manage project-scoped bookings without overlaps."
      actions={
        <>
          <Badge variant="secondary">{filteredLaboratoryResources.length || filteredResources.length} visible</Badge>
          <Badge variant={startedBookings.length ? 'warning' : 'muted'}>{startedBookings.length} immutable started</Badge>
        </>
      }
      className="resource-workspace"
    >
      <section className="panel" aria-label="Resource filters">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              Resource filters
            </h2>
            <p className="text-sm text-muted-foreground">Filter by name, type, and bookable status before choosing a reservation window.</p>
          </div>
          <Badge variant={activeFilterCount ? 'secondary' : 'muted'}>{activeFilterCount} active filters</Badge>
        </div>
        <div className="grid gap-3 lg:grid-cols-[minmax(16rem,1fr)_12rem_12rem_auto]">
          <label className="grid gap-1.5 text-sm font-bold" htmlFor="resourceSearch">
            Search resources
            <span className="relative">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <Input
                id="resourceSearch"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Resource name, type, location"
                className="pl-9"
              />
            </span>
          </label>
          <label className="grid gap-1.5 text-sm font-bold">
            Type
            <Select value={resourceType} onValueChange={setResourceType}>
              <SelectTrigger aria-label="Resource type filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                {laboratoryResourceTypes.length ? laboratoryResourceTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                )) : resourceTypes.map((type) => (
                  <SelectItem key={type.id} value={String(type.id)}>
                    {type.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <label className="grid gap-1.5 text-sm font-bold">
            Status
            <Select value={resourceStatus} onValueChange={setResourceStatus}>
              <SelectTrigger aria-label="Resource status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="bookable">Bookable</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="unavailable">Unavailable</SelectItem>
                <SelectItem value="retired">Retired</SelectItem>
                <SelectItem value="all">All statuses</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <Button type="button" variant="outline" className="self-end" onClick={() => {
            setQuery('');
            setResourceType('all');
            setResourceStatus('bookable');
          }}>
            Clear
          </Button>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(22rem,0.95fr)_minmax(24rem,1.05fr)]">
        <section className="panel" aria-label="Resource list">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2">
                <Wrench className="h-4 w-4" aria-hidden="true" />
                Resources
              </h2>
              <p className="text-sm text-muted-foreground">Only authorized project bookings can reserve these resources.</p>
            </div>
            <Badge variant="secondary">{resources.length} total</Badge>
          </div>
          {laboratoryResourcesQuery.isLoading || resourcesQuery.isLoading || resourceTypesQuery.isLoading ? <DataState state="loading" message="Loading resources." /> : null}
          {laboratoryResourcesQuery.error ? <DataState state="error" title="Resources unavailable" message={laboratoryResourcesQuery.error.message} /> : null}
          {resourcesQuery.error ? <DataState state="error" title="Booking resources unavailable" message={resourcesQuery.error.message} /> : null}
          {resourceTypesQuery.error ? <DataState state="error" title="Resource types unavailable" message={resourceTypesQuery.error.message} /> : null}
          {filteredLaboratoryResources.length === 0 && !laboratoryResourcesQuery.isLoading && !laboratoryResourcesQuery.error ? (
            <DataState state={query || resourceType !== 'all' || resourceStatus !== 'bookable' ? 'filtered-empty' : 'empty'} title="No resources" message="No resources match the current search and filter criteria." />
          ) : null}
          <ul className="resource-list">
            {filteredLaboratoryResources.map((resource) => (
              <LaboratoryResourceRow key={resource.id} resource={resource} />
            ))}
            {filteredLaboratoryResources.length === 0 && !laboratoryResourcesQuery.data ? filteredResources.map((resource) => (
              <ResourceRow key={resource.id} resource={resource} resourceType={resourceTypeById.get(resource.resourceTypeId)} />
            )) : null}
          </ul>
        </section>
        <BookingCalendar onWindowChange={setAvailabilityWindow} />
      </div>
      {canManageResources ? (
        <form className="panel grid gap-4" aria-label="Manage resource inventory" onSubmit={onCreateResource}>
          <div>
            <h2 className="flex items-center gap-2">
              <PlusCircle className="h-4 w-4" aria-hidden="true" />
              Manage inventory
            </h2>
            <p className="text-sm text-muted-foreground">Teacher and administrator controls for resource records.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="grid gap-1.5">
              <Label htmlFor="resourceName">Resource name</Label>
              <Input id="resourceName" name="name" required placeholder="Confocal microscope" />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="resourceTypeName">Resource type</Label>
              <Input id="resourceTypeName" name="resourceType" required placeholder="Microscope" />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="resourceDescription">Description</Label>
            <Textarea id="resourceDescription" name="description" placeholder="Inventory notes, location, or capabilities" />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="resourceUseInstructions">Use instructions</Label>
            <Textarea id="resourceUseInstructions" name="useInstructions" placeholder="Rules students should follow before or after use" />
          </div>
          <Button type="submit" disabled={createResourceMutation.isPending}>
            <PlusCircle className="h-4 w-4" aria-hidden="true" />
            Create resource
          </Button>
          <FormStatus error={createResourceMutation.error?.message} success={createResourceMutation.isSuccess ? 'Resource created' : undefined} />
        </form>
      ) : null}
      <ResourceUseSubmissionPanel resources={filteredLaboratoryResources} canManage={canManageResources} />
      {projectId ? (
        <BookingForm
          projectId={projectId}
          resources={filteredResources}
          resourceTypes={resourceTypes}
          defaultStartsAt={availabilityWindow.startsAt}
          defaultEndsAt={availabilityWindow.endsAt}
          disabled={!availabilityWindow.hasValidWindow}
        />
      ) : (
        <DataState state="warning" title="No project context" message="Select a project before creating a resource booking." />
      )}
      {projectId ? (
        <section className="panel" aria-label="Upcoming booking actions">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2">
                <CalendarDays className="h-4 w-4" aria-hidden="true" />
                Upcoming bookings
              </h2>
              <p className="text-sm text-muted-foreground">Future reservations can be cancelled; started reservations are immutable.</p>
            </div>
            <Badge variant="secondary">{upcomingBookings.length} active</Badge>
          </div>
          {bookingsQuery.isLoading ? <DataState state="loading" message="Loading project bookings." /> : null}
          {bookingsQuery.error ? <DataState state="error" title="Bookings unavailable" message={bookingsQuery.error.message} /> : null}
          {upcomingBookings.length === 0 && !bookingsQuery.isLoading && !bookingsQuery.error ? (
            <DataState state="empty" title="No future bookings" message="No future bookings for this project." />
          ) : null}
          <ul className="resource-list">
            {upcomingBookings.map((booking) => (
              <BookingRow key={booking.id} booking={booking} resource={resourceById.get(booking.resourceItemId)} resourceType={resourceById.get(booking.resourceItemId) ? resourceTypeById.get(resourceById.get(booking.resourceItemId)!.resourceTypeId) : undefined} projectId={projectId} />
            ))}
          </ul>
        </section>
      ) : null}
      {projectId ? <NotificationList projectId={projectId} /> : null}
    </PageShell>
  );
}

function LaboratoryResourceRow({ resource }: { resource: LaboratoryResource }) {
  return (
    <li>
      <div className="min-w-0">
        <strong>{resource.name}</strong>
        <p>
          {resource.resourceType} · {resource.useInstructions || resource.description || 'No use instructions'}
        </p>
      </div>
      <StatusBadge status={resource.status} />
    </li>
  );
}

function ResourceRow({ resource, resourceType }: { resource: ResourceItem; resourceType?: ResourceType }) {
  return (
    <li>
      <div className="min-w-0">
        <strong>{resource.name}</strong>
        <p>
          {resourceType?.name ?? 'Resource'} · {resource.location ?? 'No location'}
        </p>
      </div>
      <StatusBadge status={resource.status} />
    </li>
  );
}

function BookingRow({ booking, resource, resourceType, projectId }: { booking: Booking; resource?: ResourceItem; resourceType?: ResourceType; projectId: number }) {
  const hasStarted = new Date(booking.starts_at).getTime() <= Date.now();

  return (
    <li className="items-start">
      <div className="min-w-0">
        <strong>{resource?.name ?? `Resource #${booking.resourceItemId}`}</strong>
        {resourceType ? <p>{resourceType.name}</p> : null}
        <p>{formatDateTime(booking.starts_at)} to {formatDateTime(booking.ends_at)}</p>
        {booking.purpose ? <small className="text-muted-foreground">{booking.purpose}</small> : null}
        <div className="mt-2 flex flex-wrap gap-2">
          <StatusBadge status={booking.status} />
          {hasStarted ? <StatusBadge status="started" /> : <StatusBadge status="future" />}
        </div>
      </div>
      <BookingActions projectId={projectId} bookingId={booking.id} startsAt={booking.starts_at} compact />
    </li>
  );
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}
