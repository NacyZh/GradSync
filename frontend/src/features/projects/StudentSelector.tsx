import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { useState } from 'react';

import { Input } from '@/components/ui/input';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { searchStudents, type StudentOption } from './api';

export function StudentSelector({ onSelect, disabled = false }: { onSelect: (student: StudentOption) => void; disabled?: boolean }) {
  const [query, setQuery] = useState('');
  const { data = [], isFetching } = useQuery({
    queryKey: ['students', query],
    queryFn: () => searchStudents(query),
    enabled: query.trim().length > 0,
  });

  return (
    <div className="grid gap-2">
      <label className="grid gap-1.5 text-sm font-bold" htmlFor="student-selector">
        Student nickname
        <span className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <Input id="student-selector" className="pl-9" value={query} onChange={(event) => setQuery(event.target.value)} disabled={disabled} placeholder="Search nickname or email" />
        </span>
      </label>
      {isFetching ? <p className="text-sm text-muted-foreground">Searching students.</p> : null}
      {query.trim().length > 0 && !isFetching && data.length === 0 ? (
        <p className="text-sm text-muted-foreground">No eligible students match this search.</p>
      ) : null}
      {data.length > 0 ? (
        <ul className="grid max-h-56 gap-2 overflow-auto rounded-md border p-2">
          {data.map((student) => (
            <li key={student.id}>
              <button type="button" className="flex w-full items-center justify-between gap-3 rounded-sm px-2 py-2 text-left hover:bg-muted" onClick={() => onSelect(student)} disabled={disabled}>
                <span>
                  <strong>{student.nickname || student.email}</strong>
                  <span className="ml-2 text-sm text-muted-foreground">{student.email}</span>
                </span>
                <StatusBadge status={student.degreeType} />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
