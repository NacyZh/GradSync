import { Button } from '@/shared/ui/primitives/button';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/shared/ui/primitives/alert-dialog';
import type { LaboratoryResource } from './api';

type Props = {
  resource?: LaboratoryResource;
  open: boolean;
  pending?: boolean;
  canRetire?: boolean;
  onOpenChange: (open: boolean) => void;
  onDelete: () => void;
  onRetire: () => void;
};

export function ResourceLifecycleDialog({ resource, open, pending, canRetire, onOpenChange, onDelete, onRetire }: Props) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{canRetire ? `Retire ${resource?.name}` : `Delete ${resource?.name}`}</AlertDialogTitle>
          <AlertDialogDescription>
            {canRetire ? 'This resource has retained history. Retirement preserves it and blocks new use.' : 'This permanently removes the catalog record. An immutable deletion audit snapshot remains.'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={pending}>Cancel</AlertDialogCancel>
          <Button type="button" variant="destructive" disabled={pending} onClick={canRetire ? onRetire : onDelete}>{canRetire ? 'Retire resource' : 'Delete resource'}</Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
