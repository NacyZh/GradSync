import { useEffect, useState } from 'react';

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
  const [policy, setPolicy] = useState<ConfirmationPolicy | 'inherit'>('inherit');

  useEffect(() => setPolicy(resource?.confirmationPolicyOverride ?? 'inherit'), [resource, open]);

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
      ...(resource ? { version: resource.version } : {}),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby="resource-form-description">
        <DialogHeader>
          <DialogTitle>{resource ? `Edit ${resource.name}` : 'Create resource'}</DialogTitle>
          <DialogDescription id="resource-form-description">Name, type, and total quantity are required.</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={submit} aria-label={resource ? 'Edit resource' : 'Create resource'}>
          <div className="grid gap-1.5"><Label htmlFor="inventory-name">Resource name</Label><Input id="inventory-name" name="name" required defaultValue={resource?.name} /></div>
          <div className="grid gap-1.5"><Label htmlFor="inventory-type">Resource type</Label><Input id="inventory-type" name="resourceType" required defaultValue={resource?.resourceType} /></div>
          <div className="grid gap-1.5"><Label htmlFor="inventory-quantity">Total quantity</Label><Input id="inventory-quantity" name="totalQuantity" type="number" min={1} required defaultValue={resource?.totalQuantity ?? 1} /></div>
          <div className="grid gap-1.5"><Label htmlFor="inventory-location">Location (optional)</Label><Input id="inventory-location" name="location" defaultValue={resource?.location} /></div>
          <div className="grid gap-1.5"><Label>Confirmation policy (optional)</Label><Select value={policy} onValueChange={(value) => setPolicy(value as ConfirmationPolicy | 'inherit')}><SelectTrigger aria-label="Confirmation policy"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="inherit">Inherit type default</SelectItem><SelectItem value="immediate">Immediate</SelectItem><SelectItem value="approval_required">Approval required</SelectItem></SelectContent></Select></div>
          <div className="grid gap-1.5"><Label htmlFor="inventory-description">Description (optional)</Label><Textarea id="inventory-description" name="description" defaultValue={resource?.description} /></div>
          <div className="grid gap-1.5"><Label htmlFor="inventory-instructions">Use instructions (optional)</Label><Textarea id="inventory-instructions" name="useInstructions" defaultValue={resource?.useInstructions} /></div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" disabled={pending}>{resource ? 'Save changes' : 'Create resource'}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
