import { useQuery } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
import { useState } from 'react';

import { Button } from '../../shared/ui/primitives/button';
import { Input } from '../../shared/ui/primitives/input';
import { Label } from '../../shared/ui/primitives/label';
import { type AudienceOption, listAudienceOptions } from './api';

type Props = {
  type: 'project' | 'account';
  selected: AudienceOption[];
  onChange: (selected: AudienceOption[]) => void;
};

export function ScheduleRecipientSelector({ type, selected, onChange }: Props) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const optionsQuery = useQuery({
    queryKey: ['schedule-audience-options', type, query],
    queryFn: () => listAudienceOptions(type, query),
    enabled: open,
  });
  const selectedIds = new Set(selected.map((option) => option.id));
  const label = type === 'project' ? 'Projects' : 'Members';

  return (
    <div className="schedule-recipient-selector">
      <Label htmlFor={`schedule-${type}-search`}>{label}</Label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input
          id={`schedule-${type}-search`}
          className="pl-9"
          value={query}
          placeholder={`Search ${label.toLowerCase()}`}
          autoComplete="off"
          onFocus={() => setOpen(true)}
          onChange={(event) => { setQuery(event.target.value); setOpen(true); }}
          onKeyDown={(event) => { if (event.key === 'Escape') setOpen(false); }}
        />
        {open ? (
          <div className="schedule-recipient-options" role="listbox" aria-label={`${label} options`}>
            {optionsQuery.isLoading ? <p>Loading options</p> : null}
            {(optionsQuery.data?.results ?? []).map((option) => (
              <button
                key={option.id}
                type="button"
                role="option"
                aria-selected={selectedIds.has(option.id)}
                disabled={selectedIds.has(option.id)}
                onClick={() => { onChange([...selected, option]); setQuery(''); setOpen(false); }}
              >
                <span><strong>{option.label}</strong><small>{option.secondaryLabel}</small></span>
                {selectedIds.has(option.id) ? <span>Selected</span> : null}
              </button>
            ))}
            {!optionsQuery.isLoading && (optionsQuery.data?.results.length ?? 0) === 0 ? <p>No eligible options</p> : null}
          </div>
        ) : null}
      </div>
      {selected.length ? (
        <ul className="schedule-recipient-selected" aria-label={`Selected ${label.toLowerCase()}`}>
          {selected.map((option) => (
            <li key={option.id}>
              <span>{option.label}</span>
              <Button type="button" variant="ghost" size="icon" aria-label={`Remove ${option.label}`} onClick={() => onChange(selected.filter((candidate) => candidate.id !== option.id))}>
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
