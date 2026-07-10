import { Search } from 'lucide-react';

import { Input } from '@/shared/ui/primitives/input';

type CodeArtifactFiltersProps = {
  value: string;
  visibility: string;
  onChange: (value: string) => void;
  onVisibilityChange: (value: string) => void;
  showVisibility?: boolean;
};

export function CodeArtifactFilters({ value, visibility, onChange, onVisibilityChange, showVisibility = true }: CodeArtifactFiltersProps) {
  return (
    <div className={showVisibility ? 'grid gap-2 md:grid-cols-[minmax(16rem,1fr)_12rem]' : 'grid gap-2'}>
      <label className="block">
        <span className="sr-only">Search code artifacts</span>
        <span className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input className="pl-9" value={value} onChange={(event) => onChange(event.target.value)} placeholder="Search name, description, tag" />
        </span>
      </label>
      {showVisibility ? (
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
      ) : null}
    </div>
  );
}
