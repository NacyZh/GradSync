import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
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
import { BookingForm } from './BookingForm';
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
  const [availabilityWindow, setAvailabilityWindow] = useState({ startsAt: '', endsAt: '', hasValidWindow: true });
  const [inventoryOpen, setInventoryOpen] = useState(false);
  const [editing, setEditing] = useState<LaboratoryResource>();
  const [lifecycle, setLifecycle] = useState<LaboratoryResource>();
  const [canRetire, setCanRetire] = useState(false);

  const resourcesQuery = useQuery({ queryKey: ['resources'], queryFn: listResources });
  const typesQuery = useQuery({ queryKey: ['resource-types'], queryFn: listResourceTypes });
  const resources = useMemo(() => resourcesQuery.data?.results ?? [], [resourcesQuery.data]);
  const resourceTypes = useMemo(() => typesQuery.data?.results ?? [], [typesQuery.data]);
  const filtered = useMemo(() => resources.filter((resource) => {
    const text = `${resource.name} ${resource.resourceType} ${resource.location ?? ''}`.toLowerCase();
    return text.includes(query.toLowerCase())
      && (typeFilter === 'all' || resource.resourceType === typeFilter)
      && (statusFilter === 'all' || (statusFilter === 'bookable' ? resource.status === 'active' : resource.status === statusFilter));
  }), [query, resources, statusFilter, typeFilter]);
  const bookingResources = useMemo<ResourceItem[]>(() => filtered.map((resource) => ({
    ...resource,
    status: resource.status === 'active' ? 'available' : resource.status,
  })), [filtered]);

  const createMutation = useMutation({
    mutationFn: createLaboratoryResource,
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['resources'] }); setInventoryOpen(false); },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ResourceWrite & { version: number } }) => updateLaboratoryResource(id, payload),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['resources'] }); setInventoryOpen(false); setEditing(undefined); },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteLaboratoryResource,
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['resources'] }); setLifecycle(undefined); setCanRetire(false); },
    onError: () => setCanRetire(true),
  });
  const retireMutation = useMutation({
    mutationFn: (resource: LaboratoryResource) => retireLaboratoryResource(resource.id, resource.version),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['resources'] }); setLifecycle(undefined); setCanRetire(false); },
  });

  function openCreate() { setEditing(undefined); setInventoryOpen(true); }
  function openEdit(resource: LaboratoryResource) { setEditing(resource); setInventoryOpen(true); }
  function save(payload: ResourceWrite & { version?: number }) {
    if (editing && payload.version) updateMutation.mutate({ id: editing.id, payload: { ...payload, version: payload.version } });
    else createMutation.mutate(payload);
  }

  return (
    <PageShell
      title="Lab resources"
      description="Search shared research-group resources and manage real inventory."
      actions={<><Badge variant="secondary">{filtered.length} visible</Badge>{canManage ? <Button onClick={openCreate}><PlusCircle className="h-4 w-4" />Create resource</Button> : null}</>}
      className="resource-workspace"
    >
      <section className="panel" aria-label="Resource filters">
        <div className="mb-4 flex items-start justify-between gap-3"><div><h2 className="flex items-center gap-2"><SlidersHorizontal className="h-4 w-4" />Resource filters</h2><p className="text-sm text-muted-foreground">Filter real inventory by name, type, location, and status.</p></div></div>
        <div className="grid gap-3 lg:grid-cols-[minmax(16rem,1fr)_12rem_12rem_auto]">
          <Label className="grid gap-1.5" htmlFor="resource-search">Search resources<span className="relative"><Search className="pointer-events-none absolute left-3 top-3 h-4 w-4" /><Input id="resource-search" className="pl-9" value={query} onChange={(event) => setQuery(event.target.value)} /></span></Label>
          <Label className="grid gap-1.5">Type<Select value={typeFilter} onValueChange={setTypeFilter}><SelectTrigger aria-label="Resource type filter"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All types</SelectItem>{Array.from(new Set(resources.map((resource) => resource.resourceType))).map((type) => <SelectItem key={type} value={type}>{type}</SelectItem>)}</SelectContent></Select></Label>
          <Label className="grid gap-1.5">Status<Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger aria-label="Resource status filter"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="bookable">Bookable</SelectItem><SelectItem value="active">Active</SelectItem><SelectItem value="unavailable">Unavailable</SelectItem><SelectItem value="retired">Retired</SelectItem><SelectItem value="all">All statuses</SelectItem></SelectContent></Select></Label>
          <Button type="button" variant="outline" className="self-end" onClick={() => { setQuery(''); setTypeFilter('all'); setStatusFilter('bookable'); }}>Clear</Button>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(22rem,0.95fr)_minmax(24rem,1.05fr)]">
        <section className="panel" aria-label="Resource list">
          <div className="mb-4"><h2 className="flex items-center gap-2"><Wrench className="h-4 w-4" />Resources</h2><p className="text-sm text-muted-foreground">Quantity and confirmation policy are shown for each shared resource.</p></div>
          {resourcesQuery.isLoading ? <DataState state="loading" message="Loading resources." /> : null}
          {resourcesQuery.error ? <DataState state="error" title="Resources unavailable" message={resourcesQuery.error.message} /> : null}
          {!resourcesQuery.isLoading && filtered.length === 0 ? <DataState state={query || typeFilter !== 'all' || statusFilter !== 'bookable' ? 'filtered-empty' : 'empty'} title="No resources" message={canManage ? 'Create the first real resource to begin.' : 'No shared resources are currently available.'} /> : null}
          <ul className="resource-list">
            {filtered.map((resource) => <li key={resource.id} className="items-start"><div className="min-w-0"><strong>{resource.name}</strong><p>{resource.resourceType} · {resource.location || 'No location'}</p><p>{resource.availableQuantity ?? resource.totalQuantity} of {resource.totalQuantity} available · {resource.effectiveConfirmationPolicy === 'immediate' ? 'Immediate confirmation' : 'Approval required'}</p></div><div className="flex flex-wrap items-center justify-end gap-2"><StatusBadge status={resource.status} />{canManage ? <><Button size="sm" variant="outline" onClick={() => openEdit(resource)}><Pencil className="h-4 w-4" />Edit</Button><Button size="sm" variant="destructive" onClick={() => { setCanRetire(false); setLifecycle(resource); }}><Trash2 className="h-4 w-4" />Delete</Button></> : null}</div></li>)}
          </ul>
        </section>
        <BookingCalendar onWindowChange={setAvailabilityWindow} />
      </div>

      <ResourceUseSubmissionPanel resources={filtered} canManage={canManage} />
      <BookingForm resources={bookingResources} resourceTypes={resourceTypes} defaultStartsAt={availabilityWindow.startsAt} defaultEndsAt={availabilityWindow.endsAt} disabled={!availabilityWindow.hasValidWindow} />

      <ResourceInventoryDialog open={inventoryOpen} resource={editing} pending={createMutation.isPending || updateMutation.isPending} error={createMutation.error?.message ?? updateMutation.error?.message} onOpenChange={(open) => { setInventoryOpen(open); if (!open) setEditing(undefined); }} onSubmit={save} />
      <ResourceLifecycleDialog resource={lifecycle} open={Boolean(lifecycle)} pending={deleteMutation.isPending || retireMutation.isPending} error={deleteMutation.error?.message ?? retireMutation.error?.message} canRetire={canRetire} onOpenChange={(open) => { if (!open) { setLifecycle(undefined); setCanRetire(false); } }} onDelete={() => lifecycle && deleteMutation.mutate(lifecycle.id)} onRetire={() => lifecycle && retireMutation.mutate(lifecycle)} />
    </PageShell>
  );
}
