import { Search } from 'lucide-react';

import { Input } from '@/components/ui/input';

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
  const activeFilters = [
    value ? `Search: ${value}` : '',
    author ? `Author: ${author}` : '',
    year ? `Year: ${year}` : '',
    keyword ? `Keyword: ${keyword}` : '',
  ].filter(Boolean);

  return (
    <div className="grid gap-2">
      <div className="grid gap-2 md:grid-cols-[minmax(16rem,1fr)_10rem_8rem_10rem]">
        <label className="block">
          <span className="sr-only">Search papers</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input className="pl-9" value={value} onChange={(event) => onChange(event.target.value)} placeholder="Search title, author, year, keyword" />
          </span>
        </label>
        <Input aria-label="Author filter" value={author} onChange={(event) => onAuthorChange?.(event.target.value)} placeholder="Author" />
        <Input aria-label="Year filter" value={year} onChange={(event) => onYearChange?.(event.target.value)} placeholder="Year" inputMode="numeric" />
        <Input aria-label="Keyword filter" value={keyword} onChange={(event) => onKeywordChange?.(event.target.value)} placeholder="Keyword" />
        {visibility !== undefined && onVisibilityChange ? (
          <label className="block md:col-span-1">
            <span className="sr-only">Visibility filter</span>
            <select
              aria-label="Visibility filter"
              className="min-h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={visibility}
              onChange={(event) => onVisibilityChange(event.target.value)}
            >
              <option value="">All visibility</option>
              <option value="project_members">Project members</option>
              <option value="group_wide">Group wide</option>
            </select>
          </label>
        ) : null}
      </div>
      {activeFilters.length ? (
        <p className="text-sm text-muted-foreground" aria-live="polite">
          Active filters: {activeFilters.join(', ')}
        </p>
      ) : null}
    </div>
  );
}
