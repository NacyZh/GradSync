import { eachDayOfInterval, endOfMonth, endOfWeek, format, isSameDay, isSameMonth, isToday, startOfMonth, startOfWeek } from 'date-fns';
import { useState } from 'react';

import { CalendarAgenda } from './CalendarAgenda';
import type { CalendarOccurrence, CalendarView } from './api';
import { formatOccurrenceTime, occurrenceStart } from './api';

type Props = {
  anchor: Date;
  view: Exclude<CalendarView, 'agenda'>;
  occurrences: CalendarOccurrence[];
  selectedId: string | null;
  onSelect: (occurrence: CalendarOccurrence) => void;
};

export function CalendarGrid({ anchor, view, occurrences, selectedId, onSelect }: Props) {
  const [expandedDays, setExpandedDays] = useState<string[]>([]);
  const start = view === 'month' ? startOfWeek(startOfMonth(anchor), { weekStartsOn: 1 }) : view === 'week' ? startOfWeek(anchor, { weekStartsOn: 1 }) : anchor;
  const end = view === 'month' ? endOfWeek(endOfMonth(anchor), { weekStartsOn: 1 }) : view === 'week' ? endOfWeek(anchor, { weekStartsOn: 1 }) : anchor;
  const days = eachDayOfInterval({ start, end });
  const weekdays = eachDayOfInterval({ start: startOfWeek(anchor, { weekStartsOn: 1 }), end: endOfWeek(anchor, { weekStartsOn: 1 }) });
  const gridClass = {
    month: 'calendar-grid-month',
    week: 'calendar-grid-week',
    day: 'calendar-grid-day',
  }[view];

  return (
    <>
      <div className="calendar-desktop-surface">
        {view !== 'day' ? (
          <div className="calendar-weekdays" role="row" aria-label="Weekdays">
            {weekdays.map((day) => <span key={day.toISOString()} role="columnheader">{format(day, 'EEE')}</span>)}
          </div>
        ) : null}
        <div className={`calendar-grid ${gridClass}`} role="grid" aria-label={`${view} calendar`}>
          {days.map((day) => {
            const dayKey = format(day, 'yyyy-MM-dd');
            const dayOccurrences = occurrences.filter((item) => isSameDay(occurrenceStart(item), day));
            const itemLimit = view === 'month' ? 3 : 6;
            const expanded = expandedDays.includes(dayKey);
            const visibleItems = expanded ? dayOccurrences : dayOccurrences.slice(0, itemLimit);
            const hiddenCount = dayOccurrences.length - visibleItems.length;
            return (
              <section
                key={day.toISOString()}
                className="calendar-day"
                role="gridcell"
                aria-label={format(day, 'EEEE, MMMM d')}
                data-today={isToday(day) || undefined}
                data-outside={view === 'month' && !isSameMonth(day, anchor) || undefined}
              >
                <time dateTime={dayKey}>{format(day, view === 'day' ? 'EEEE, MMMM d' : 'd')}</time>
                <div className="calendar-day-items">
                  {visibleItems.map((item) => (
                    <button
                      key={item.occurrenceId}
                      type="button"
                      className={`calendar-occurrence source-${item.sourceType}`}
                      aria-label={`${item.title}, ${formatOccurrenceTime(item)}, ${item.sourceType}`}
                      aria-pressed={selectedId === item.occurrenceId}
                      onClick={() => onSelect(item)}
                    >
                      <span>{formatOccurrenceTime(item)}</span>
                      <strong>{item.title}</strong>
                      <small>{item.sourceType}</small>
                    </button>
                  ))}
                  {hiddenCount > 0 ? (
                    <button type="button" className="calendar-more" onClick={() => setExpandedDays((current) => [...current, dayKey])}>
                      +{hiddenCount} more
                    </button>
                  ) : null}
                </div>
              </section>
            );
          })}
        </div>
      </div>
      <div className="calendar-mobile-surface">
        <CalendarAgenda occurrences={occurrences} selectedId={selectedId} onSelect={onSelect} />
      </div>
    </>
  );
}
