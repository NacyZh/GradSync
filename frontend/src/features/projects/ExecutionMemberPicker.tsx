import { Check, ChevronsUpDown } from 'lucide-react';
import { useMemo, useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/shared/ui/primitives/popover';
import { cn } from '@/shared/lib/utils';
import { useI18n } from '@/shared/i18n/I18nProvider';

import type { ProjectMembership } from './api';

type Props = {
  label: string;
  members: ProjectMembership[];
  value: number[];
  onChange: (ids: number[]) => void;
  eligibleRoles?: ProjectMembership['role'][];
};

export function ExecutionMemberPicker({
  label,
  members,
  value,
  onChange,
  eligibleRoles,
}: Props) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const options = useMemo(
    () =>
      members.filter((member) => {
        const userId = member.userId ?? member.user_id;
        if (!userId || member.status !== 'active') return false;
        if (eligibleRoles && !eligibleRoles.includes(member.role)) return false;
        const text = `${member.nickname ?? ''} ${member.name ?? ''} ${member.email ?? ''}`;
        return text.toLowerCase().includes(query.trim().toLowerCase());
      }),
    [eligibleRoles, members, query],
  );
  const selectedNames = members
    .filter((member) => value.includes(member.userId ?? member.user_id ?? -1))
    .map((member) => member.nickname || member.name || member.email)
    .filter(Boolean);

  return (
    <div className="grid gap-1.5">
      <span className="text-sm font-bold">{label}</span>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full min-w-0 justify-between font-normal"
          >
            <span className="truncate">
              {selectedNames.length ? selectedNames.join(', ') : t('selectMembers')}
            </span>
            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-60" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-[min(24rem,calc(100vw-3rem))] p-2">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('searchProjectMembers')}
            aria-label={`Search ${label.toLowerCase()}`}
          />
          <div className="mt-2 max-h-56 overflow-y-auto" role="listbox" aria-multiselectable>
            {options.map((member) => {
              const userId = member.userId ?? member.user_id;
              if (!userId) return null;
              const selected = value.includes(userId);
              const name = member.nickname || member.name || member.email || `User ${userId}`;
              return (
                <button
                  key={`${member.id}-${userId}`}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className="flex w-full min-w-0 items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() =>
                    onChange(
                      selected
                        ? value.filter((id) => id !== userId)
                        : [...value, userId],
                    )
                  }
                >
                  <Check
                    className={cn('h-4 w-4 shrink-0', !selected && 'opacity-0')}
                    aria-hidden="true"
                  />
                  <span className="min-w-0 flex-1 truncate">{name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {member.role}
                  </span>
                </button>
              );
            })}
            {!options.length ? (
              <p className="px-2 py-3 text-sm text-muted-foreground">{t('noMatchingMembers')}</p>
            ) : null}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
