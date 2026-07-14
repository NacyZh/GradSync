import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Pencil, PlusCircle, Search, SlidersHorizontal, Trash2, Wrench } from 'lucide-react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { useAuth } from '../auth/AuthProvider';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { BookingCalendar } from './BookingCalendar';
import type { LaboratoryResource, ResourceItem, ResourceWrite } from './api';
import {
  createLaboratoryResource,
  deleteLaboratoryResource,
  listResourceTypes,
  listResources,
  retireLaboratoryResource,
  updateLaboratoryResource,
} from './api';
import { ResourceInventoryDialog } from './ResourceInventoryDialog';
import { ResourceLifecycleDialog } from './ResourceLifecycleDialog';
import { ResourceUseSubmissionPanel } from './ResourceUseSubmissionPanel';

export function ResourceListPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManage = user?.global_role === 'advisor' || user?.global_role === 'admin';
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('bookable');
  const [selectedResourceId, setSelectedResourceId] = useState<number | undefined>();
  const [availability, setAvailability] = useState<ResourceItem[]>([]);
  const [inventoryOpen, setInventoryOpen] = useState(false);
  const [editing, setEditing] = useState<LaboratoryResource>();
  const [lifecycle, setLifecycle] = useState<LaboratoryResource>();
  const [canRetire, setCanRetire] = useState(false);

  const resourcesQuery = useQuery({ queryKey: ['resources'], queryFn: listResources });
  const typesQuery = useQuery({ queryKey: ['resource-types'], queryFn: listResourceTypes });
  const resources = useMemo(() => resourcesQuery.data?.results ?? [], [resourcesQuery.data]);
  const resourceTypes = useMemo(() => typesQuery.data?.results ?? [], [typesQuery.data]);
  const resourceTypeById = useMemo(() => new Map(resourceTypes.map((type) => [type.id, type.name])), [resourceTypes]);
  const availabilityById = useMemo(() => new Map(availability.map((resource) => [resource.id, resource])), [availability]);
  const resourceTypeOptions = useMemo(() => Array.from(new Set(resources.map((resource) => getResourceTypeName(resource, resourceTypeById)).filter(Boolean))).sort(), [resourceTypeById, resources]);
  const filtered = useMemo(() => resources.filter((resource) => {
    const typeName = getResourceTypeName(resource, resourceTypeById);
    const cardStatus = getResourceCardStatus(resource, availabilityById.get(resource.id));
    const text = `${resource.name} ${typeName} ${resource.location ?? ''}`.toLowerCase();
    return text.includes(query.toLowerCase())
      && (typeFilter === 'all' || typeName === typeFilter)
      && (statusFilter === 'all' || (statusFilter === 'bookable' ? resource.status === 'active' : cardStatus === statusFilter));
  }), [availabilityById, query, resourceTypeById, resources, statusFilter, typeFilter]);
  const selectedResource = filtered.find((resource) => resource.id === selectedResourceId) ?? filtered[0];

  useEffect(() => {
    if (!filtered.length) {
      setSelectedResourceId(undefined);
      return;
    }
    if (!selectedResourceId || !filtered.some((resource) => resource.id === selectedResourceId)) {
      setSelectedResourceId(filtered[0].id);
    }
  }, [filtered, selectedResourceId]);

  const createMutation = useMutation({
    mutationFn: createLaboratoryResource,
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['resources'] }), queryClient.invalidateQueries({ queryKey: ['resource-availability'] })]); setInventoryOpen(false); },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ResourceWrite & { version: number } }) => updateLaboratoryResource(id, payload),
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['resources'] }), queryClient.invalidateQueries({ queryKey: ['resource-availability'] })]); setInventoryOpen(false); setEditing(undefined); },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteLaboratoryResource,
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['resources'] }), queryClient.invalidateQueries({ queryKey: ['resource-availability'] })]); setLifecycle(undefined); setCanRetire(false); },
    onError: () => setCanRetire(true),
  });
  const retireMutation = useMutation({
    mutationFn: (resource: LaboratoryResource) => retireLaboratoryResource(resource.id, resource.version),
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['resources'] }), queryClient.invalidateQueries({ queryKey: ['resource-availability'] })]); setLifecycle(undefined); setCanRetire(false); },
  });

  function openCreate() { setEditing(undefined); setInventoryOpen(true); }
  function openEdit(resource: LaboratoryResource) { setEditing(resource); setInventoryOpen(true); }
  function save(payload: ResourceWrite & { version?: number }) {
    if (editing && payload.version) updateMutation.mutate({ id: editing.id, payload: { ...payload, version: payload.version } });
    else {
      setInventoryOpen(false);
      createMutation.mutate(payload);
    }
  }

  function selectResource(resourceId: number) {
    setSelectedResourceId(resourceId);
  }

  function onResourceCardKeyDown(event: React.KeyboardEvent<HTMLLIElement>, resourceId: number) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectResource(resourceId);
    }
  }

  return (
    <PageShell
      title="Lab resources"
      description="Search shared research-group resources and manage real inventory."
      actions={<><Badge variant="secondary">{filtered.length} visible</Badge>{canManage && !inventoryOpen ? <Button onClick={openCreate}><PlusCircle className="h-4 w-4" />Create resource</Button> : null}</>}
      className="resource-workspace"
    >
      <section className="panel" aria-label="Resource filters">
        <div className="mb-4 flex items-start justify-between gap-3"><div><h2 className="flex items-center gap-2"><SlidersHorizontal className="h-4 w-4" />Resource filters</h2><p className="text-sm text-muted-foreground">Filter real inventory by name, type, location, and status.</p></div></div>
        <div className="grid gap-3 lg:grid-cols-[minmax(16rem,1fr)_12rem_12rem_auto]">
          <Label className="grid gap-1.5" htmlFor="resource-search">Search resources<span className="relative"><Search className="pointer-events-none absolute left-3 top-3 h-4 w-4" /><Input id="resource-search" className="pl-9" value={query} onChange={(event) => setQuery(event.target.value)} /></span></Label>
          <Label className="grid gap-1.5">Type<Select value={typeFilter} onValueChange={setTypeFilter}><SelectTrigger aria-label="Resource type filter"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All types</SelectItem>{resourceTypeOptions.map((type) => <SelectItem key={type} value={type}>{type}</SelectItem>)}</SelectContent></Select></Label>
          <Label className="grid gap-1.5">Status<Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger aria-label="Resource status filter"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="bookable">Bookable</SelectItem><SelectItem value="available">Available</SelectItem><SelectItem value="unavailable">Unavailable</SelectItem><SelectItem value="retired">Retired</SelectItem><SelectItem value="all">All statuses</SelectItem></SelectContent></Select></Label>
          <Button type="button" variant="outline" className="self-end" onClick={() => { setQuery(''); setTypeFilter('all'); setStatusFilter('bookable'); }}>Clear</Button>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(22rem,0.95fr)_minmax(24rem,1.05fr)]">
        <section className="panel" aria-label="Resource list">
          <div className="mb-4"><h2 className="flex items-center gap-2"><Wrench className="h-4 w-4" />Resources</h2><p className="text-sm text-muted-foreground">Quantity and confirmation policy are shown for each shared resource.</p></div>
          {resourcesQuery.isLoading ? <DataState state="loading" message="Loading resources." /> : null}
          {resourcesQuery.error ? <DataState state="error" title="Resources unavailable" message={resourcesQuery.error.message} /> : null}
          {!resourcesQuery.isLoading && filtered.length === 0 ? <DataState state={query || typeFilter !== 'all' || statusFilter !== 'bookable' ? 'filtered-empty' : 'empty'} title="No resources" message={canManage ? 'Create the first real resource to begin.' : 'No shared resources are currently available.'} /> : null}
          <ul className="resource-list max-h-[45rem] overflow-y-auto pr-1">
            {filtered.map((resource) => (
              <li
                key={resource.id}
                role="button"
                tabIndex={0}
                aria-pressed={selectedResource?.id === resource.id}
                onClick={() => selectResource(resource.id)}
                onKeyDown={(event) => onResourceCardKeyDown(event, resource.id)}
                className={`min-h-24 cursor-pointer items-start transition hover:border-primary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${selectedResource?.id === resource.id ? 'ring-2 ring-primary/40' : ''}`}
              >
                <div className="min-w-0">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <strong className="min-w-0 truncate">{resource.name}</strong>
                    <Badge variant="secondary">
                      {resource.effectiveConfirmationPolicy === 'immediate' ? 'Immediate confirmation' : 'Approval required'}
                    </Badge>
                  </div>
                  <p>{getResourceTypeName(resource, resourceTypeById)} · {resource.location || 'No location'}</p>
                  <p>{formatAvailabilitySummary(resource, availabilityById.get(resource.id))}</p>
                  <ResourceUsePeriods resource={resource} availability={availabilityById.get(resource.id)} />
                </div>
                <div className="flex flex-col items-end gap-2 text-right">
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <StatusBadge status={getResourceCardStatus(resource, availabilityById.get(resource.id))} />
                    {canManage ? <><Button size="sm" variant="outline" onClick={(event) => { event.stopPropagation(); openEdit(resource); }}><Pencil className="h-4 w-4" />Edit</Button><Button size="sm" variant="destructive" onClick={(event) => { event.stopPropagation(); setCanRetire(false); setLifecycle(resource); }}><Trash2 className="h-4 w-4" />Delete</Button></> : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
        <BookingCalendar
          resource={selectedResource}
          resourceTypes={resourceTypes}
          onAvailabilityChange={setAvailability}
        />
      </div>

      <ResourceUseSubmissionPanel resources={filtered} canManage={canManage} />

      <ResourceInventoryDialog open={inventoryOpen} resource={editing} pending={createMutation.isPending || updateMutation.isPending} error={createMutation.error?.message ?? updateMutation.error?.message} onOpenChange={(open) => { setInventoryOpen(open); if (!open) setEditing(undefined); }} onSubmit={save} />
      <ResourceLifecycleDialog resource={lifecycle} open={Boolean(lifecycle)} pending={deleteMutation.isPending || retireMutation.isPending} error={deleteMutation.error?.message ?? retireMutation.error?.message} canRetire={canRetire} onOpenChange={(open) => { if (!open) { setLifecycle(undefined); setCanRetire(false); } }} onDelete={() => lifecycle && deleteMutation.mutate(lifecycle.id)} onRetire={() => lifecycle && retireMutation.mutate(lifecycle)} />
    </PageShell>
  );
}

function formatAvailabilitySummary(resource: LaboratoryResource, availability?: ResourceItem) {
  const totalQuantity = availability?.totalQuantity ?? resource.totalQuantity ?? 0;
  const availableQuantity = availability?.availableQuantity ?? resource.availableQuantity ?? totalQuantity;
  const allocatedQuantity = availability?.allocatedQuantity ?? Math.max(totalQuantity - availableQuantity, 0);
  return `${availableQuantity} of ${totalQuantity} available · ${allocatedQuantity} in use`;
}

function getResourceTypeName(resource: LaboratoryResource, resourceTypeById: Map<number, string>) {
  return resource.resourceType || resourceTypeById.get(resource.resourceTypeId) || 'Resource';
}

function getResourceCardStatus(resource: LaboratoryResource, availability?: ResourceItem) {
  if (resource.status === 'retired') return 'retired';
  if (resource.status === 'unavailable') return 'unavailable';
  if (!availability) return resource.status === 'active' ? 'available' : resource.status;
  const availableQuantity = availability.availableQuantity ?? availability.totalQuantity ?? resource.availableQuantity ?? resource.totalQuantity ?? 0;
  return availableQuantity > 0 ? 'available' : 'unavailable';
}

function ResourceUsePeriods({ resource, availability }: { resource: LaboratoryResource; availability?: ResourceItem }) {
  const periods = availability?.currentUsePeriods ?? resource.currentUsePeriods ?? [];
  if (!periods.length) return null;
  return (
    <div className="mt-2 grid gap-1">
      {periods.slice(0, 2).map((period) => (
        <small key={period.bookingId} className="text-muted-foreground">
          In use {formatDateTime(period.startsAt)} – {formatDateTime(period.endsAt)} · Qty {period.quantity}
        </small>
      ))}
    </div>
  );
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
