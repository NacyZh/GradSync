import { Badge, type BadgeProps } from '@/shared/ui/primitives/badge';
import { cn } from '@/shared/lib/utils';

type StatusBadgeProps = {
  status: string;
  className?: string;
};

const statusVariant: Record<string, BadgeProps['variant']> = {
  active: 'success',
  available: 'success',
  completed: 'success',
  reviewed: 'success',
  delivered: 'success',
  sent: 'success',
  approved: 'success',
  blocked: 'warning',
  archived: 'warning',
  unavailable: 'warning',
  needs_revision: 'warning',
  pending: 'warning',
  pending_role_activation: 'warning',
  pending_email_verification: 'warning',
  queued: 'warning',
  retry_needed: 'destructive',
  skipped: 'warning',
  failed: 'destructive',
  rejected: 'destructive',
  cancelled: 'destructive',
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const label = status.replaceAll('_', ' ');
  return (
    <Badge variant={statusVariant[status] ?? 'muted'} className={cn('capitalize', className)}>
      {label}
    </Badge>
  );
}
