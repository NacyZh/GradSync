import { Search } from 'lucide-react';

import { Input } from '@/components/ui/input';

export function PaperFilters({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="sr-only">Search papers</span>
      <span className="relative block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input className="pl-9" value={value} onChange={(event) => onChange(event.target.value)} placeholder="Search title, author, venue, DOI, tag" />
      </span>
    </label>
  );
}
