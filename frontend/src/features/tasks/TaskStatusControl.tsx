import { useMutation } from '@tanstack/react-query';
import {
  CircleCheck,
  CircleDashed,
  CircleX,
  LoaderCircle,
  OctagonAlert,
  Send,
  type LucideIcon,
} from 'lucide-react';

import { cn } from '@/shared/lib/utils';
import { useI18n, type MessageKey } from '@/shared/i18n/I18nProvider';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { updateTask, type Task } from './api';

type StatusOption = {
  value: string;
  labelKey: MessageKey;
  icon: LucideIcon;
  iconClassName: string;
};

const STATUS_OPTIONS: StatusOption[] = [
  { value: 'not_started', labelKey: 'statusNotStarted', icon: CircleDashed, iconClassName: 'text-muted-foreground' },
  { value: 'in_progress', labelKey: 'statusInProgress', icon: LoaderCircle, iconClassName: 'text-sky-600' },
  { value: 'blocked', labelKey: 'statusBlocked', icon: OctagonAlert, iconClassName: 'text-amber-600' },
  { value: 'submitted', labelKey: 'statusSubmitted', icon: Send, iconClassName: 'text-teal-600' },
  { value: 'completed', labelKey: 'statusCompleted', icon: CircleCheck, iconClassName: 'text-emerald-600' },
  { value: 'cancelled', labelKey: 'statusCancelled', icon: CircleX, iconClassName: 'text-destructive' },
];

export function TaskStatusControl({
  projectId,
  taskId,
  status,
  disabled = false,
  onUpdated,
}: {
  projectId: number;
  taskId: number;
  status: string;
  disabled?: boolean;
  onUpdated?: (task: Task) => void;
}) {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const mutation = useMutation({
    mutationFn: (nextStatus: string) => updateTask(projectId, taskId, { status: nextStatus }),
    onSuccess: (task) => {
      onUpdated?.(task);
      notify('Task status updated', 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const activeStatus = mutation.isPending ? mutation.variables : status;

  return (
    <div id={`task-${taskId}-status`} className="grid min-w-0 gap-2">
      <p className="text-sm font-bold">Task status</p>
      <div
        role="radiogroup"
        aria-label="Task status"
        aria-busy={mutation.isPending}
        className="grid min-w-0 grid-cols-2 gap-1 rounded-md bg-muted p-1 sm:grid-cols-3"
      >
        {STATUS_OPTIONS.map((option) => {
          const Icon = option.icon;
          const selected = activeStatus === option.value;
          const label = t(option.labelKey);
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected}
              title={label}
              disabled={disabled || mutation.isPending}
              className={cn(
                'flex min-h-11 min-w-0 items-center justify-center gap-2 rounded px-2 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-muted',
                selected
                  ? 'border border-border bg-background text-foreground shadow-sm'
                  : 'border border-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground',
              )}
              onClick={() => {
                if (option.value !== status) mutation.mutate(option.value);
              }}
            >
              <Icon className={cn('h-4 w-4 shrink-0', option.iconClassName)} aria-hidden="true" />
              <span className="min-w-0 truncate">{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
