import { CalendarClock, ChevronRight, UserRound } from 'lucide-react';

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
  projectId?: number;
  selectedTaskId?: number;
  memberNameById?: Map<number, string>;
  onSelectTask?: (task: TaskNode) => void;
};

function formatDate(value?: string) {
  if (!value) return null;
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
}

function priorityTone(priority?: string) {
  if (priority === 'urgent' || priority === 'high') return 'text-destructive';
  if (priority === 'low') return 'text-muted-foreground';
  return 'text-foreground';
}

export function TaskTree({ tasks, projectId, selectedTaskId, memberNameById, onSelectTask }: TaskTreeProps) {
  return (
    <ul className="task-tree" aria-label="Task hierarchy" data-density="compact">
      {tasks.map((task) => (
        <li key={task.id} id={`task-${task.id}`}>
          <details open className={selectedTaskId === task.id ? 'ring-2 ring-ring ring-offset-2 ring-offset-background' : undefined}>
            <summary className="group">
              <ChevronRight className="h-4 w-4 shrink-0 transition-transform group-open:rotate-90" aria-hidden="true" />
              <span className="task-title min-w-0 flex-1 truncate">{task.title}</span>
              <StatusBadge status={task.status ?? 'not_started'} />
              {task.deadline_at ? (
                <time className="hidden text-xs text-muted-foreground sm:inline" dateTime={task.deadline_at}>
                  {formatDate(task.deadline_at)}
                </time>
              ) : null}
            </summary>
            <div className="task-meta">
              <span className={priorityTone(task.priority)}>Priority: {task.priority ?? 'normal'}</span>
              <span className="inline-flex items-center gap-1">
                <UserRound className="h-3.5 w-3.5" aria-hidden="true" />
                Assignees: {formatAssignees(task, memberNameById)}
              </span>
              {task.deadline_at ? (
                <span className="inline-flex items-center gap-1">
                  <CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />
                  Due {formatDate(task.deadline_at)}
                </span>
              ) : null}
              {projectId ? (
                <a
                  href={`#task-${task.id}-status`}
                  className="inline-action font-bold text-primary"
                  onClick={() => onSelectTask?.(task)}
                >
                  Update status
                </a>
              ) : null}
            </div>
            {task.children && task.children.length > 0 ? (
              <TaskTree tasks={task.children} projectId={projectId} selectedTaskId={selectedTaskId} memberNameById={memberNameById} onSelectTask={onSelectTask} />
            ) : null}
          </details>
        </li>
      ))}
    </ul>
  );
}

function formatAssignees(task: TaskNode, memberNameById?: Map<number, string>) {
  const assigneeIds = task.assignee_ids?.length ? task.assignee_ids : task.assignee_id ? [task.assignee_id] : [];
  if (!assigneeIds.length) return 'Unassigned';
  return assigneeIds.map((userId) => memberNameById?.get(userId) ?? `User ${userId}`).join(', ');
}
