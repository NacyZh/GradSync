import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { searchStudents, type StudentOption } from './api';

type StudentSelectorProps = {
  onSelect: (student: StudentOption) => void;
  disabled?: boolean;
  projectId?: number;
  selectedIds?: number[];
};

const EMPTY_SELECTED_IDS: number[] = [];

export function StudentSelector({ onSelect, disabled = false, projectId, selectedIds = EMPTY_SELECTED_IDS }: StudentSelectorProps) {
  const [query, setQuery] = useState('');
  const [selectedStudentId, setSelectedStudentId] = useState('');
  const { data = [], isFetching } = useQuery({
    queryKey: ['students', query, projectId],
    queryFn: () => searchStudents(query, projectId),
    enabled: query.trim().length > 0,
  });
  const selectableStudents = useMemo(
    () => data.filter((student) => !selectedIds.includes(student.id) && student.eligibility?.selectable !== false),
    [data, selectedIds],
  );
  const selectedStudent = data.find((student) => String(student.id) === selectedStudentId);

  useEffect(() => {
    if (!selectableStudents.some((student) => String(student.id) === selectedStudentId)) {
      setSelectedStudentId(selectableStudents[0] ? String(selectableStudents[0].id) : '');
    }
  }, [selectableStudents, selectedStudentId]);

  function selectCurrentStudent() {
    if (!selectedStudent || selectedIds.includes(selectedStudent.id) || selectedStudent.eligibility?.selectable === false) return;
    onSelect(selectedStudent);
  }

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
        <div className="grid gap-2">
          <label className="grid gap-1.5 text-sm font-bold" htmlFor="student-option-selector">
            Student account
            <select
              id="student-option-selector"
              className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={selectedStudentId}
              onChange={(event) => setSelectedStudentId(event.target.value)}
              disabled={disabled || selectableStudents.length === 0}
            >
              {selectableStudents.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.label || `${student.nickname || student.email} <${student.email}>`}
                </option>
              ))}
            </select>
          </label>
          <Button type="button" variant="outline" onClick={selectCurrentStudent} disabled={disabled || !selectedStudent}>
            Select student
          </Button>
        </div>
      ) : null}
      {data.length > 0 ? (
        <ul className="grid max-h-56 gap-2 overflow-auto rounded-md border p-2" aria-label="Student search results">
          {data.map((student) => (
            <li key={student.id}>
              <div className="flex w-full items-center justify-between gap-3 rounded-sm px-2 py-2 text-left">
                <span>
                  <strong>{student.nickname || student.email}</strong>
                  <span className="ml-2 text-sm text-muted-foreground">{student.email}</span>
                  {selectedIds.includes(student.id) ? <span className="ml-2 text-xs text-muted-foreground">Selected</span> : null}
                  {student.eligibility?.selectable === false ? (
                    <span className="ml-2 text-xs text-muted-foreground">Already a member</span>
                  ) : null}
                </span>
                {student.degreeType ? <StatusBadge status={student.degreeType} /> : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
