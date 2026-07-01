import { Badge, type BadgeProps } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

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
  blocked: 'warning',
  archived: 'warning',
  unavailable: 'warning',
  needs_revision: 'warning',
  failed: 'destructive',
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
