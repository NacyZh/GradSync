import { ChevronRight } from 'lucide-react';

import { StatusBadge } from '../../shared/ui/StatusBadge';

export type TaskNode = {
  id: number;
  title: string;
  description?: string;
  status?: string;
  priority?: string;
  deadline_at?: string;
  assignee_id?: number;
  assignee_ids?: number[];
  children?: TaskNode[];
};

type TaskTreeProps = {
  tasks: TaskNode[];
  selectedTaskId?: number;
  onSelectTask?: (task: TaskNode) => void;
};

export function TaskTree({ tasks, selectedTaskId, onSelectTask }: TaskTreeProps) {
  return (
    <ul className="grid gap-2" aria-label="Task plan">
      {tasks.map((task) => (
        <li key={task.id} id={`task-${task.id}`}>
          <button
            type="button"
            className={`grid min-h-12 w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-md border px-3 py-2 text-left transition-colors hover:bg-muted ${selectedTaskId === task.id ? 'border-primary bg-muted ring-2 ring-ring ring-offset-2 ring-offset-background' : ''}`}
            aria-current={selectedTaskId === task.id ? 'true' : undefined}
            onClick={() => onSelectTask?.(task)}
          >
            <span className="flex min-w-0 items-center gap-2">
              {task.children?.length ? <ChevronRight className="h-4 w-4 shrink-0" aria-hidden="true" /> : <span className="h-4 w-4 shrink-0" aria-hidden="true" />}
              <span className="min-w-0 truncate font-semibold">{task.title}</span>
            </span>
            <span className="shrink-0">
              <StatusBadge status={task.status ?? 'not_started'} />
            </span>
          </button>
          {task.children && task.children.length > 0 ? (
            <div className="ml-4 mt-2 border-l pl-3">
              <TaskTree tasks={task.children} selectedTaskId={selectedTaskId} onSelectTask={onSelectTask} />
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
