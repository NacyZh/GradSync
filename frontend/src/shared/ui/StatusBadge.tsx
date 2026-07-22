import { Badge, type BadgeProps } from '@/shared/ui/primitives/badge';
import { cn } from '@/shared/lib/utils';
import { useI18n, type MessageKey } from '@/shared/i18n/I18nProvider';

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

const statusLabel: Record<string, MessageKey> = {
  active: 'statusActive', available: 'statusAvailable', completed: 'statusCompleted',
  reviewed: 'statusReviewed', delivered: 'statusDelivered', sent: 'statusSent',
  approved: 'statusApproved', blocked: 'statusBlocked', archived: 'statusArchived',
  unavailable: 'statusUnavailable', needs_revision: 'statusNeedsRevision', pending: 'statusPending',
  pending_role_activation: 'statusPendingRoleActivation', pending_email_verification: 'statusPendingEmailVerification',
  queued: 'statusQueued', retry_needed: 'statusRetryNeeded', skipped: 'statusSkipped', failed: 'statusFailed',
  rejected: 'statusRejected', cancelled: 'statusCancelled', suspended: 'statusSuspended',
  student: 'statusStudent', teacher: 'statusTeacher', advisor: 'statusAdvisor', administrator: 'statusAdministrator',
  admin: 'statusAdmin', masters: 'statusMasters', doctoral: 'statusDoctoral', draft: 'statusDraft',
  submitted: 'statusSubmitted', in_progress: 'statusInProgress', not_started: 'statusNotStarted',
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { locale, t } = useI18n();
  const label = locale === 'zh' && statusLabel[status] ? t(statusLabel[status]) : status.replaceAll('_', ' ');
  return (
    <Badge variant={statusVariant[status] ?? 'muted'} className={cn('capitalize', className)}>
      {label}
    </Badge>
  );
}
