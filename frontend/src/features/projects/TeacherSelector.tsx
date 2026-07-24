import { useQuery } from '@tanstack/react-query';
import { Check, ChevronsUpDown, Search } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/primitives/popover';
import { useI18n } from '@/shared/i18n/I18nProvider';

import { searchEligibleTeachers, type TeacherOption } from './api';

export function TeacherSelector({
  projectId,
  value,
  onSelect,
  disabled,
}: {
  projectId: number;
  value?: TeacherOption | null;
  onSelect: (teacher: TeacherOption) => void;
  disabled?: boolean;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const normalized = query.trim();
  const teachersQuery = useQuery({
    queryKey: ['eligible-project-teachers', projectId, normalized],
    queryFn: () => searchEligibleTeachers(normalized, projectId),
    enabled: open && normalized.length >= 2,
  });
  const results = teachersQuery.data?.results ?? [];

  return (
    <div className="grid min-w-0 gap-1.5">
      <Label>{t('teacherAccount')}</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-label={t('teacherAccount')}
            aria-expanded={open}
            className="w-full min-w-0 justify-between"
            disabled={disabled}
          >
            <span className="truncate">{value?.label ?? t('searchEligibleTeachers')}</span>
            <ChevronsUpDown className="h-4 w-4 flex-none" aria-hidden="true" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[min(24rem,calc(100vw-2rem))] p-2" align="start">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <Input
              aria-label={t('searchEligibleTeachers')}
              className="pl-8"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              autoFocus
            />
          </div>
          <div className="mt-2 max-h-56 overflow-y-auto" role="listbox">
            {normalized.length < 2 ? (
              <p className="p-3 text-sm text-muted-foreground">{t('enterTwoCharacters')}</p>
            ) : teachersQuery.isLoading ? (
              <p className="p-3 text-sm text-muted-foreground">{t('searching')}</p>
            ) : results.length ? (
              results.map((teacher) => (
                <Button
                  key={teacher.id}
                  type="button"
                  variant="ghost"
                  role="option"
                  aria-selected={value?.id === teacher.id}
                  className="h-auto w-full justify-start gap-2 py-2 text-left"
                  onClick={() => {
                    onSelect(teacher);
                    setOpen(false);
                  }}
                >
                  <Check className={`h-4 w-4 ${value?.id === teacher.id ? 'opacity-100' : 'opacity-0'}`} aria-hidden="true" />
                  <span className="grid min-w-0">
                    <strong className="truncate text-sm">{teacher.label}</strong>
                    <span className="truncate text-xs text-muted-foreground">{teacher.email}</span>
                  </span>
                </Button>
              ))
            ) : (
              <p className="p-3 text-sm text-muted-foreground">{t('noEligibleTeachers')}</p>
            )}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
