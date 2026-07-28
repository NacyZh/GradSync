import { CalendarDays, UserRound } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { cn } from '@/shared/lib/utils';
import { formatUiDate } from '@/shared/i18n/translate';
import { translateUiText } from '@/shared/i18n/translate';
import { useI18n } from '@/shared/i18n/I18nProvider';

import type { Deliverable } from './executionApi';

type Props = {
  deliverables: Deliverable[];
  selectedId: number | null;
  onSelect: (deliverable: Deliverable) => void;
};

export function DeliverableList({ deliverables, selectedId, onSelect }: Props) {
  const { locale } = useI18n();
  return (
    <div className="min-h-0 overflow-y-auto pr-1" aria-label="Deliverable list">
      <div className="grid gap-2">
        {deliverables.map((deliverable) => (
          <Button
            key={deliverable.id}
            type="button"
            variant="ghost"
            className={cn(
              'h-auto min-h-24 w-full items-start justify-start whitespace-normal border px-3 py-3 text-left',
              selectedId === deliverable.id && 'border-primary bg-accent',
            )}
            onClick={() => onSelect(deliverable)}
          >
            <span className="grid min-w-0 flex-1 gap-2">
              <span className="flex min-w-0 items-start justify-between gap-2">
                <span className="truncate font-extrabold">{deliverable.title}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {translateUiText(deliverable.status.replaceAll('_', ' '), locale)}
                </span>
              </span>
              <span className="h-1.5 overflow-hidden rounded-full bg-muted">
                <span
                  className="block h-full bg-primary"
                  style={{ width: `${deliverable.progressPercent}%` }}
                />
              </span>
              <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <CalendarDays className="h-3.5 w-3.5" />
                  {formatUiDate(deliverable.dueDate)}
                </span>
                <span className="inline-flex min-w-0 items-center gap-1">
                  <UserRound className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">
                    {deliverable.assignees.map((item) => item.name).join(', ')}
                  </span>
                </span>
              </span>
            </span>
          </Button>
        ))}
      </div>
    </div>
  );
}
