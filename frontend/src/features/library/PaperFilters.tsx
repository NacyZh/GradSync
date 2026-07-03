import { Search } from 'lucide-react';

import { Input } from '@/components/ui/input';

type PaperFiltersProps = {
  value: string;
  visibility: string;
  onChange: (value: string) => void;
  onVisibilityChange: (value: string) => void;
};

export function PaperFilters({ value, visibility, onChange, onVisibilityChange }: PaperFiltersProps) {
  return (
    <div className="grid gap-2 md:grid-cols-[minmax(16rem,1fr)_12rem]">
      <label className="block">
        <span className="sr-only">Search papers</span>
        <span className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input className="pl-9" value={value} onChange={(event) => onChange(event.target.value)} placeholder="Search title, author, year, keyword" />
        </span>
      </label>
      <label className="block">
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
    </div>
  );
}
