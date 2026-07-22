import { format } from 'date-fns';

import { formatUiDate } from '../../shared/i18n/translate';
import type { CalendarOccurrence } from './api';
import { formatOccurrenceTime, occurrenceStart } from './api';

type Props = {
  occurrences: CalendarOccurrence[];
  selectedId: string | null;
  onSelect: (occurrence: CalendarOccurrence) => void;
};

export function CalendarAgenda({ occurrences, selectedId, onSelect }: Props) {
  const sorted = [...occurrences].sort((left, right) => occurrenceStart(left).getTime() - occurrenceStart(right).getTime());
  if (sorted.length === 0) {
    return <p className="calendar-empty" role="status">No schedule items in this period.</p>;
  }
  const grouped = sorted.reduce<Map<string, CalendarOccurrence[]>>((result, item) => {
    const key = format(occurrenceStart(item), 'yyyy-MM-dd');
    result.set(key, [...(result.get(key) ?? []), item]);
    return result;
  }, new Map());
  const groups = Array.from(grouped);
  return (
    <div className="calendar-agenda" aria-label="Calendar agenda">
      {groups.map(([day, items]) => (
        <section className="calendar-agenda-group" key={day}>
          <header>
            <time dateTime={day}>{formatUiDate(occurrenceStart(items[0]), { weekday: 'long', month: 'long', day: 'numeric' })}</time>
            <span>{items.length} {items.length === 1 ? 'item' : 'items'}</span>
          </header>
          <ol>
            {items.map((item) => (
              <li key={item.occurrenceId}>
                <button
                  type="button"
                  className={`calendar-agenda-item source-${item.sourceType}`}
                  aria-label={`${item.title}, ${formatOccurrenceTime(item)}, ${item.sourceType}, ${item.status}`}
                  aria-pressed={selectedId === item.occurrenceId}
                  onClick={() => onSelect(item)}
                >
                  <span className="calendar-agenda-time">{formatOccurrenceTime(item)}</span>
                  <strong>{item.title}</strong>
                  <span className="calendar-source-label">{sourceLabel(item.sourceType)}</span>
                  <small>{item.status.replaceAll('_', ' ')}</small>
                </button>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function sourceLabel(source: CalendarOccurrence['sourceType']) {
  return source.charAt(0).toUpperCase() + source.slice(1);
}
