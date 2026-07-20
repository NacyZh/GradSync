import { addDays, addMonths, addWeeks, format } from 'date-fns';
import { CalendarDays, ChevronLeft, ChevronRight, Plus, SlidersHorizontal } from 'lucide-react';

import { Button } from '../../shared/ui/primitives/button';
import { Popover, PopoverContent, PopoverTrigger } from '../../shared/ui/primitives/popover';
import type { CalendarSource, CalendarView } from './api';

const views: Array<{ value: CalendarView; label: string }> = [
  { value: 'month', label: 'Month' },
  { value: 'week', label: 'Week' },
  { value: 'day', label: 'Day' },
  { value: 'agenda', label: 'Agenda' },
];
const sourceOptions: Array<{ value: CalendarSource; label: string }> = [
  { value: 'schedule', label: 'Schedule' },
  { value: 'project', label: 'Projects' },
  { value: 'task', label: 'Tasks' },
  { value: 'report', label: 'Reports' },
  { value: 'booking', label: 'Bookings' },
];

type Props = {
  anchor: Date;
  view: CalendarView;
  sources: CalendarSource[];
  onAnchorChange: (date: Date) => void;
  onViewChange: (view: CalendarView) => void;
  onSourcesChange: (sources: CalendarSource[]) => void;
  onCreate?: () => void;
};

export function CalendarToolbar({ anchor, view, sources, onAnchorChange, onViewChange, onSourcesChange, onCreate }: Props) {
  const shift = (amount: number) => {
    const next = view === 'month'
      ? addMonths(anchor, amount)
      : view === 'week'
        ? addWeeks(anchor, amount)
        : addDays(anchor, amount);
    onAnchorChange(next);
  };

  return (
    <header className="calendar-toolbar">
      <div className="calendar-toolbar-heading">
        <span className="calendar-toolbar-kicker"><CalendarDays className="h-4 w-4" aria-hidden="true" /> Schedule</span>
        <h2>{format(anchor, view === 'month' ? 'MMMM yyyy' : 'MMM d, yyyy')}</h2>
      </div>
      <div className="calendar-toolbar-actions">
        {onCreate ? <Button type="button" size="sm" onClick={onCreate}><Plus className="h-4 w-4" aria-hidden="true" /> New schedule</Button> : null}
        <Popover>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label={`Filter calendar sources, ${sources.length} selected`}
            >
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              Sources <span className="calendar-filter-count">{sources.length}</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-64 p-2">
            <fieldset className="calendar-source-filters" aria-label="Calendar sources">
              <legend>Show in calendar</legend>
              {sourceOptions.map((option) => (
                <label key={option.value}>
                  <input
                    type="checkbox"
                    checked={sources.includes(option.value)}
                    onChange={() => onSourcesChange(
                      sources.includes(option.value)
                        ? sources.filter((source) => source !== option.value)
                        : [...sources, option.value],
                    )}
                  />
                  <span className={`calendar-source-mark source-${option.value}`} aria-hidden="true" />
                  <span>{option.label}</span>
                </label>
              ))}
            </fieldset>
          </PopoverContent>
        </Popover>
      </div>
      <div className="calendar-toolbar-lower">
        <div className="calendar-period-controls">
          <Button type="button" size="icon" variant="ghost" aria-label="Previous period" title="Previous period" onClick={() => shift(-1)}>
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={() => onAnchorChange(new Date())}>Today</Button>
          <Button type="button" size="icon" variant="ghost" aria-label="Next period" title="Next period" onClick={() => shift(1)}>
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        <div className="calendar-view-switch" role="group" aria-label="Calendar view">
          {views.map((option) => (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant="ghost"
              className={view === option.value ? 'active' : undefined}
              aria-pressed={view === option.value}
              onClick={() => onViewChange(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>
    </header>
  );
}
