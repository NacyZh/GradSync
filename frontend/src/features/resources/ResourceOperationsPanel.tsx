import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Boxes, CircleDollarSign, Gauge, Wrench } from 'lucide-react';
import { useState } from 'react';

import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatUiDate, translateUiText } from '@/shared/i18n/translate';
import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { DataState } from '@/shared/ui/DataState';
import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { Textarea } from '@/shared/ui/primitives/textarea';

import {
  createConsumableTransaction,
  createResourceMaintenance,
  listConsumableTransactions,
  listResourceMaintenance,
  updateResourceMaintenance,
} from './api';
import type { ConsumableTransaction, LaboratoryResource, ResourceMaintenance } from './api';
import { listProjects } from '../projects';

type Props = {
  resource?: LaboratoryResource;
  canManage: boolean;
};

export function ResourceOperationsPanel({ resource, canManage }: Props) {
  const { locale } = useI18n();
  const tr = (value: string) => translateUiText(value, locale);

  if (!resource) {
    return <section className="panel" aria-label="Resource operations"><DataState state="empty" title={tr('Select a resource')} message={tr('Maintenance and stock history appear here.')} /></section>;
  }
  return resource.kind === 'consumable'
    ? <ConsumablePanel resource={resource} canManage={canManage} tr={tr} />
    : <MaintenancePanel resource={resource} canManage={canManage} tr={tr} />;
}

function MaintenancePanel({ resource, canManage, tr }: Props & { resource: LaboratoryResource; tr: (value: string) => string }) {
  const queryClient = useQueryClient();
  const { notify } = useAppFeedback();
  const [kind, setKind] = useState<ResourceMaintenance['kind']>('preventive');
  const query = useQuery({
    queryKey: ['resource-maintenance', resource.id],
    queryFn: () => listResourceMaintenance(resource.id),
    enabled: canManage,
  });
  const createMutation = useMutation({
    mutationFn: createResourceMaintenance,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['resource-maintenance', resource.id] }),
        queryClient.invalidateQueries({ queryKey: ['resources'] }),
      ]);
      notify(tr('Maintenance record created'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const transitionMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ResourceMaintenance['status'] }) => updateResourceMaintenance(id, { status }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['resource-maintenance', resource.id] }),
        queryClient.invalidateQueries({ queryKey: ['resources'] }),
      ]);
      notify(tr('Maintenance status updated'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const scheduledAt = String(form.get('scheduledAt'));
    const dueAt = String(form.get('dueAt'));
    createMutation.mutate({
      resourceId: resource.id,
      kind,
      title: String(form.get('title') ?? '').trim(),
      scheduledAt: new Date(scheduledAt).toISOString(),
      dueAt: dueAt ? new Date(dueAt).toISOString() : null,
      provider: String(form.get('provider') ?? '').trim(),
      details: String(form.get('details') ?? '').trim(),
      takesOffline: form.get('takesOffline') === 'on',
      cost: Number(form.get('cost') ?? 0),
    });
    event.currentTarget.reset();
  }

  const records = query.data?.results ?? [];
  return (
    <section className="panel min-h-0" aria-label="Maintenance and calibration">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="flex items-center gap-2"><Wrench className="h-4 w-4" />{tr('Maintenance and calibration')}</h2><p className="text-sm text-muted-foreground">{tr('Faults and offline work immediately affect booking availability.')}</p></div>
        {resource.nextCalibrationAt ? <Badge variant="secondary"><Gauge className="h-3.5 w-3.5" />{tr('Next calibration')} {formatUiDate(resource.nextCalibrationAt)}</Badge> : null}
      </div>
      <div className="grid min-h-0 gap-4 lg:grid-cols-[minmax(18rem,0.85fr)_minmax(20rem,1.15fr)]">
        {canManage ? <form className="grid content-start gap-3" aria-label="Create maintenance record" onSubmit={submit}>
          <Label className="grid gap-1.5">{tr('Work type')}<Select value={kind} onValueChange={(value) => setKind(value as ResourceMaintenance['kind'])}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="preventive">{tr('Preventive maintenance')}</SelectItem><SelectItem value="calibration">{tr('Calibration')}</SelectItem><SelectItem value="repair">{tr('Repair')}</SelectItem><SelectItem value="fault">{tr('Fault')}</SelectItem></SelectContent></Select></Label>
          <Label className="grid gap-1.5" htmlFor="maintenance-title">{tr('Title')}<Input id="maintenance-title" name="title" required /></Label>
          <div className="grid grid-cols-2 gap-3"><Label className="grid gap-1.5" htmlFor="maintenance-start">{tr('Start')}<Input id="maintenance-start" name="scheduledAt" type="datetime-local" required /></Label><Label className="grid gap-1.5" htmlFor="maintenance-due">{tr('Expected finish')}<Input id="maintenance-due" name="dueAt" type="datetime-local" /></Label></div>
          <Label className="grid gap-1.5" htmlFor="maintenance-provider">{tr('Provider')}<Input id="maintenance-provider" name="provider" /></Label>
          <Label className="grid gap-1.5" htmlFor="maintenance-cost">{tr('Cost')}<Input id="maintenance-cost" name="cost" type="number" min={0} step="0.01" defaultValue={0} /></Label>
          <Label className="flex items-center gap-2"><input name="takesOffline" type="checkbox" defaultChecked />{tr('Take resource offline')}</Label>
          <Label className="grid gap-1.5" htmlFor="maintenance-details">{tr('Details')}<Textarea id="maintenance-details" name="details" /></Label>
          <Button type="submit" disabled={createMutation.isPending}>{tr('Create work order')}</Button>
        </form> : null}
        {canManage ? <div className="min-h-0">
          {query.isLoading ? <DataState state="loading" message={tr('Loading maintenance history.')} /> : null}
          {!query.isLoading && records.length === 0 ? <DataState state="empty" title={tr('No maintenance history')} message={tr('Scheduled work, faults, repairs, and calibration appear here.')} /> : null}
          <ul className="resource-list max-h-[34rem] overflow-y-auto pr-1">
            {records.map((record) => <li key={record.id} className="items-start">
              <div className="min-w-0"><strong>{record.title}</strong><p>{tr(record.kind)} · {formatUiDate(record.scheduledAt)}</p><p>{record.provider || tr('Internal')} · {tr('Cost')} {record.cost}</p>{record.details ? <p>{record.details}</p> : null}</div>
              <div className="flex flex-col items-end gap-2"><Badge variant={record.status === 'completed' ? 'secondary' : 'outline'}>{tr(record.status)}</Badge>{canManage && record.status === 'scheduled' ? <div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => transitionMutation.mutate({ id: record.id, status: 'in_progress' })}>{tr('Start')}</Button><Button size="sm" variant="ghost" onClick={() => transitionMutation.mutate({ id: record.id, status: 'cancelled' })}>{tr('Cancel')}</Button></div> : null}{canManage && record.status === 'in_progress' ? <Button size="sm" onClick={() => transitionMutation.mutate({ id: record.id, status: 'completed' })}>{tr('Complete')}</Button> : null}</div>
            </li>)}
          </ul>
        </div> : null}
      </div>
    </section>
  );
}

function ConsumablePanel({ resource, canManage, tr }: Props & { resource: LaboratoryResource; tr: (value: string) => string }) {
  const queryClient = useQueryClient();
  const { notify } = useAppFeedback();
  const [kind, setKind] = useState<ConsumableTransaction['kind']>('issue');
  const [projectId, setProjectId] = useState('unassigned');
  const projectsQuery = useQuery({
    queryKey: ['projects', 'resource-cost-options'],
    queryFn: listProjects,
    enabled: canManage,
  });
  const query = useQuery({
    queryKey: ['consumable-transactions', resource.id],
    queryFn: () => listConsumableTransactions(resource.id),
    enabled: canManage,
  });
  const mutation = useMutation({
    mutationFn: createConsumableTransaction,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['consumable-transactions', resource.id] }),
        queryClient.invalidateQueries({ queryKey: ['resources'] }),
      ]);
      notify(tr('Stock transaction recorded'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const quantity = Number(form.get('quantity'));
    mutation.mutate({
      resourceId: resource.id,
      projectId: projectId === 'unassigned' ? null : Number(projectId),
      kind,
      quantityDelta: kind === 'issue' ? -Math.abs(quantity) : kind === 'receipt' ? Math.abs(quantity) : quantity,
      unitCost: form.get('unitCost') ? Number(form.get('unitCost')) : null,
      note: String(form.get('note') ?? '').trim(),
    });
    event.currentTarget.reset();
  }

  const transactions = query.data?.results ?? [];
  return (
    <section className="panel min-h-0" aria-label="Consumable inventory">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="flex items-center gap-2"><Boxes className="h-4 w-4" />{tr('Consumable inventory')}</h2><p className="text-sm text-muted-foreground">{tr('Receipts, issues, adjustments, and cost snapshots are retained as an immutable ledger.')}</p></div>
        <div className="flex gap-2"><Badge variant={resource.lowStock ? 'destructive' : 'secondary'}>{resource.lowStock ? <AlertTriangle className="h-3.5 w-3.5" /> : null}{resource.stockOnHand} {resource.stockUnit}</Badge>{canManage ? <Badge variant="outline"><CircleDollarSign className="h-3.5 w-3.5" />{resource.unitCost}/{resource.stockUnit}</Badge> : null}</div>
      </div>
      {canManage ? <div className="grid min-h-0 gap-4 lg:grid-cols-[minmax(17rem,0.75fr)_minmax(21rem,1.25fr)]">
        <form className="grid content-start gap-3" aria-label="Record stock transaction" onSubmit={submit}>
          <Label className="grid gap-1.5">{tr('Transaction type')}<Select value={kind} onValueChange={(value) => setKind(value as ConsumableTransaction['kind'])}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="receipt">{tr('Receipt')}</SelectItem><SelectItem value="issue">{tr('Issue')}</SelectItem><SelectItem value="adjustment">{tr('Adjustment')}</SelectItem></SelectContent></Select></Label>
          <Label className="grid gap-1.5">{tr('Charge to project')}<Select value={projectId} onValueChange={setProjectId}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="unassigned">{tr('Unassigned')}</SelectItem>{(projectsQuery.data?.results ?? []).filter((project) => project.status === 'active').map((project) => <SelectItem key={project.id} value={String(project.id)}>{project.title}</SelectItem>)}</SelectContent></Select></Label>
          <Label className="grid gap-1.5" htmlFor="stock-quantity">{tr('Quantity')}<Input id="stock-quantity" name="quantity" type="number" required min={kind === 'adjustment' ? undefined : 1} /></Label>
          <Label className="grid gap-1.5" htmlFor="stock-unit-cost">{tr('Unit cost snapshot')}<Input id="stock-unit-cost" name="unitCost" type="number" min={0} step="0.01" placeholder={resource.unitCost} /></Label>
          <Label className="grid gap-1.5" htmlFor="stock-note">{tr('Purpose or note')}<Textarea id="stock-note" name="note" /></Label>
          <Button type="submit" disabled={mutation.isPending}>{tr('Record transaction')}</Button>
        </form>
        <div className="min-h-0">
          {query.isLoading ? <DataState state="loading" message={tr('Loading stock ledger.')} /> : null}
          {!query.isLoading && transactions.length === 0 ? <DataState state="empty" title={tr('No stock history')} message={tr('The first receipt, issue, or adjustment will appear here.')} /> : null}
          <ul className="resource-list max-h-[30rem] overflow-y-auto pr-1">
            {transactions.map((transaction) => <li key={transaction.id} className="items-start"><div><strong>{tr(transaction.kind)} {transaction.quantityDelta > 0 ? '+' : ''}{transaction.quantityDelta} {resource.stockUnit}</strong><p>{formatUiDate(transaction.recordedAt)} · {tr('Balance')} {transaction.balanceAfter}</p>{transaction.note ? <p>{transaction.note}</p> : null}</div><div className="text-right"><Badge variant="outline">{tr('Cost')} {transaction.totalCost}</Badge></div></li>)}
          </ul>
        </div>
      </div> : <p className="text-sm text-muted-foreground">{tr('Ask a teacher or administrator to issue consumables from stock.')}</p>}
    </section>
  );
}
