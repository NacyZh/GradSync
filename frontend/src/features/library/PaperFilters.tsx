import { Search } from 'lucide-react';

import { Input } from '@/components/ui/input';

import { useI18n } from '../i18n/I18nProvider';

type PaperFiltersProps = {
  value: string;
  author?: string;
  year?: string;
  keyword?: string;
  visibility?: string;
  onChange: (value: string) => void;
  onAuthorChange?: (value: string) => void;
  onYearChange?: (value: string) => void;
  onKeywordChange?: (value: string) => void;
  onVisibilityChange?: (value: string) => void;
};

export function PaperFilters({
  value,
  author = '',
  year = '',
  keyword = '',
  visibility,
  onChange,
  onAuthorChange,
  onYearChange,
  onKeywordChange,
  onVisibilityChange,
}: PaperFiltersProps) {
  const { t } = useI18n();
  const activeFilters = [
    value ? `${t('paperLibrarySearchFilterPrefix')} ${value}` : '',
    author ? `${t('paperLibraryAuthorFilterPrefix')} ${author}` : '',
    year ? `${t('paperLibraryYearFilterPrefix')} ${year}` : '',
    keyword ? `${t('paperLibraryKeywordFilterPrefix')} ${keyword}` : '',
  ].filter(Boolean);

  return (
    <div className="grid gap-2">
      <div className="grid min-w-0 gap-2 sm:grid-cols-2">
        <label className="block min-w-0 sm:col-span-2">
          <span className="sr-only">{t('paperLibrarySearchPapers')}</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input className="pl-9" value={value} onChange={(event) => onChange(event.target.value)} placeholder={t('paperLibrarySearchPlaceholder')} />
          </span>
        </label>
        <Input aria-label={t('paperLibraryAuthorFilter')} value={author} onChange={(event) => onAuthorChange?.(event.target.value)} placeholder={t('paperLibraryAuthorPlaceholder')} />
        <Input aria-label={t('paperLibraryYearFilter')} value={year} onChange={(event) => onYearChange?.(event.target.value)} placeholder={t('paperLibraryYearPlaceholder')} inputMode="numeric" />
        <Input aria-label={t('paperLibraryKeywordFilter')} value={keyword} onChange={(event) => onKeywordChange?.(event.target.value)} placeholder={t('paperLibraryKeywordPlaceholder')} />
        {visibility !== undefined && onVisibilityChange ? (
          <label className="block md:col-span-1">
            <span className="sr-only">{t('paperLibraryVisibilityFilter')}</span>
            <select
              aria-label={t('paperLibraryVisibilityFilter')}
              className="min-h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={visibility}
              onChange={(event) => onVisibilityChange(event.target.value)}
            >
              <option value="">{t('paperLibraryAllVisibility')}</option>
              <option value="project_members">{t('paperLibraryProjectMembers')}</option>
              <option value="group_wide">{t('paperLibraryGroupWide')}</option>
            </select>
          </label>
        ) : null}
      </div>
      {activeFilters.length ? (
        <p className="text-sm text-muted-foreground" aria-live="polite">
          {t('paperLibraryActiveFilters')} {activeFilters.join(', ')}
        </p>
      ) : null}
    </div>
  );
}
