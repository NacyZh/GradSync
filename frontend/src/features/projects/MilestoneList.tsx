import { CalendarDays, CheckCircle2 } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { cn } from '@/shared/lib/utils';
import { formatUiDate } from '@/shared/i18n/translate';
import { translateUiText } from '@/shared/i18n/translate';
import { useI18n } from '@/shared/i18n/I18nProvider';

import type { Milestone } from './executionApi';

type Props = {
  milestones: Milestone[];
  selectedId: number | null;
  onSelect: (milestone: Milestone) => void;
};

export function MilestoneList({ milestones, selectedId, onSelect }: Props) {
  const { locale } = useI18n();
  return (
    <div className="min-h-0 overflow-y-auto pr-1" aria-label="Milestone list">
      <div className="grid gap-2">
        {milestones.map((milestone) => (
          <Button
            key={milestone.id}
            type="button"
            variant="ghost"
            className={cn(
              'h-auto min-h-20 w-full items-start justify-start whitespace-normal border px-3 py-3 text-left',
              selectedId === milestone.id && 'border-primary bg-accent',
            )}
            onClick={() => onSelect(milestone)}
          >
            <span className="grid min-w-0 flex-1 gap-2">
              <span className="flex min-w-0 items-start justify-between gap-2">
                <span className="truncate font-extrabold">{milestone.title}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {translateUiText(milestone.status.replaceAll('_', ' '), locale)}
                </span>
              </span>
              <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <CalendarDays className="h-3.5 w-3.5" />
                  {formatUiDate(milestone.targetDate)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {milestone.acceptedDeliverables}/{milestone.requiredDeliverables}
                </span>
              </span>
            </span>
          </Button>
        ))}
      </div>
    </div>
  );
}
