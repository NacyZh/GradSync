import { useEffect, useState } from 'react';

import { useI18n } from '@/shared/i18n/I18nProvider';
import { translateUiText } from '@/shared/i18n/translate';
import { Button } from '@/shared/ui/primitives/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/primitives/dialog';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { Textarea } from '@/shared/ui/primitives/textarea';
import type { ConfirmationPolicy, LaboratoryResource, ResourceWrite } from './api';

type Props = {
  open: boolean;
  resource?: LaboratoryResource;
  pending?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: ResourceWrite & { version?: number }) => void;
};

export function ResourceInventoryDialog({ open, resource, pending, onOpenChange, onSubmit }: Props) {
  const { locale } = useI18n();
  const tr = (value: string) => translateUiText(value, locale);
  const [policy, setPolicy] = useState<ConfirmationPolicy | 'inherit'>('inherit');
  const [kind, setKind] = useState<LaboratoryResource['kind']>('equipment');

  useEffect(() => setPolicy(resource?.confirmationPolicyOverride ?? 'inherit'), [resource, open]);
  useEffect(() => setKind(resource?.kind ?? 'equipment'), [resource, open]);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSubmit({
      name: String(form.get('name') ?? '').trim(),
      resourceType: String(form.get('resourceType') ?? '').trim(),
      totalQuantity: Number(form.get('totalQuantity')),
      location: String(form.get('location') ?? '').trim(),
      description: String(form.get('description') ?? '').trim(),
      useInstructions: String(form.get('useInstructions') ?? '').trim(),
      confirmationPolicyOverride: policy === 'inherit' ? null : policy,
      kind,
      ...(!resource ? { stockOnHand: Number(form.get('stockOnHand') ?? 0) } : {}),
      reorderLevel: Number(form.get('reorderLevel') ?? 0),
      stockUnit: String(form.get('stockUnit') ?? '').trim(),
      unitCost: Number(form.get('unitCost') ?? 0),
      calibrationIntervalDays: form.get('calibrationIntervalDays') ? Number(form.get('calibrationIntervalDays')) : null,
      nextCalibrationAt: String(form.get('nextCalibrationAt') ?? '') || null,
      ...(resource ? { version: resource.version } : {}),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby="resource-form-description">
        <DialogHeader>
          <DialogTitle>{resource ? `${tr('Edit')} ${resource.name}` : tr('Create resource')}</DialogTitle>
          <DialogDescription id="resource-form-description">{tr('Name and type are required. Equipment also requires a bookable quantity; consumables require a stock unit.')}</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={submit} aria-label={resource ? tr('Edit resource') : tr('Create resource')}>
          <div className="grid gap-1.5"><Label htmlFor="inventory-name">{tr('Resource name')}</Label><Input id="inventory-name" name="name" required defaultValue={resource?.name} /></div>
          <div className="grid gap-1.5"><Label htmlFor="inventory-type">{tr('Resource type')}</Label><Input id="inventory-type" name="resourceType" required defaultValue={resource?.resourceType} /></div>
          <div className="grid gap-1.5"><Label>{tr('Inventory class')}</Label><Select value={kind} onValueChange={(value) => setKind(value as LaboratoryResource['kind'])}><SelectTrigger aria-label={tr('Inventory class')}><SelectValue /></SelectTrigger><SelectContent><SelectItem value="equipment">{tr('Equipment')}</SelectItem><SelectItem value="consumable">{tr('Consumable')}</SelectItem></SelectContent></Select></div>
          {kind === 'equipment' ? <div className="grid gap-1.5"><Label htmlFor="inventory-quantity">{tr('Total quantity')}</Label><Input id="inventory-quantity" name="totalQuantity" type="number" min={1} required defaultValue={resource?.totalQuantity ?? 1} /></div> : <input type="hidden" name="totalQuantity" value={1} />}
          {kind === 'consumable' ? <>
            <div className="grid gap-1.5"><Label htmlFor="inventory-stock">{tr('Stock on hand')}</Label><Input id="inventory-stock" name={resource ? undefined : 'stockOnHand'} type="number" min={0} disabled={Boolean(resource)} defaultValue={resource?.stockOnHand ?? 0} /></div>
            <div className="grid gap-1.5"><Label htmlFor="inventory-reorder">{tr('Low-stock threshold')}</Label><Input id="inventory-reorder" name="reorderLevel" type="number" min={0} defaultValue={resource?.reorderLevel ?? 0} /></div>
            <div className="grid gap-1.5"><Label htmlFor="inventory-unit">{tr('Stock unit')}</Label><Input id="inventory-unit" name="stockUnit" required defaultValue={resource?.stockUnit} placeholder={tr('box, bottle, piece')} /></div>
            <div className="grid gap-1.5"><Label htmlFor="inventory-unit-cost">{tr('Unit cost')}</Label><Input id="inventory-unit-cost" name="unitCost" type="number" min={0} step="0.01" defaultValue={resource?.unitCost ?? 0} /></div>
          </> : <>
            <div className="grid gap-1.5"><Label htmlFor="inventory-calibration-cycle">{tr('Calibration cycle (days)')}</Label><Input id="inventory-calibration-cycle" name="calibrationIntervalDays" type="number" min={1} defaultValue={resource?.calibrationIntervalDays ?? ''} /></div>
            <div className="grid gap-1.5"><Label htmlFor="inventory-next-calibration">{tr('Next calibration')}</Label><Input id="inventory-next-calibration" name="nextCalibrationAt" type="date" defaultValue={resource?.nextCalibrationAt ?? ''} /></div>
          </>}
          <div className="grid gap-1.5"><Label htmlFor="inventory-location">{tr('Location (optional)')}</Label><Input id="inventory-location" name="location" defaultValue={resource?.location} /></div>
          <div className="grid gap-1.5"><Label>{tr('Confirmation policy (optional)')}</Label><Select value={policy} onValueChange={(value) => setPolicy(value as ConfirmationPolicy | 'inherit')}><SelectTrigger aria-label={tr('Confirmation policy')}><SelectValue /></SelectTrigger><SelectContent><SelectItem value="inherit">{tr('Inherit type default')}</SelectItem><SelectItem value="immediate">{tr('Immediate')}</SelectItem><SelectItem value="approval_required">{tr('Approval required')}</SelectItem></SelectContent></Select></div>
          <div className="grid gap-1.5"><Label htmlFor="inventory-description">{tr('Description (optional)')}</Label><Textarea id="inventory-description" name="description" defaultValue={resource?.description} /></div>
          <div className="grid gap-1.5"><Label htmlFor="inventory-instructions">{tr('Use instructions (optional)')}</Label><Textarea id="inventory-instructions" name="useInstructions" defaultValue={resource?.useInstructions} /></div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>{tr('Cancel')}</Button><Button type="submit" disabled={pending}>{resource ? tr('Save changes') : tr('Create resource')}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
