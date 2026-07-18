import { ChevronRight, Trash2 } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { Button } from '../../shared/ui/primitives/button';
import { deleteTask } from './api';

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
  onSelectTask?: (task: TaskNode) => void;
  canDeleteTasks?: boolean;
  onTaskDeleted?: () => Promise<unknown> | unknown;
};

export function TaskTree({ tasks, projectId, selectedTaskId, onSelectTask, canDeleteTasks = false, onTaskDeleted }: TaskTreeProps) {
  return (
    <ul className="grid gap-2" aria-label="Task plan">
      {tasks.map((task) => (
        <li key={task.id} id={`task-${task.id}`}>
          <div
            className={`grid min-h-12 w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-md border px-2 py-2 transition-colors hover:bg-muted ${selectedTaskId === task.id ? 'border-primary bg-muted ring-2 ring-ring ring-offset-2 ring-offset-background' : ''}`}
          >
            <button
              type="button"
              className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 text-left"
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
            {canDeleteTasks && projectId ? (
              <TaskDeleteButton projectId={projectId} task={task} onDeleted={onTaskDeleted} />
            ) : null}
          </div>
          {task.children && task.children.length > 0 ? (
            <div className="ml-4 mt-2 border-l pl-3">
              <TaskTree
                tasks={task.children}
                projectId={projectId}
                selectedTaskId={selectedTaskId}
                onSelectTask={onSelectTask}
                canDeleteTasks={canDeleteTasks}
                onTaskDeleted={onTaskDeleted}
              />
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function TaskDeleteButton({ projectId, task, onDeleted }: { projectId: number; task: TaskNode; onDeleted?: () => Promise<unknown> | unknown }) {
  const { confirm, notify } = useAppFeedback();
  const deleteMutation = useMutation({
    mutationFn: () => deleteTask(projectId, task.id),
    onSuccess: async () => {
      notify('Task deleted', 'success');
      await onDeleted?.();
    },
    onError: (error) => notify(error.message, 'error'),
  });

  async function onDeleteTask() {
    const ok = await confirm({
      title: 'Delete task?',
      message: `Delete "${task.title}" and its subtasks from this project. This action cannot be undone.`,
      actionLabel: 'Delete task',
    });
    if (ok) deleteMutation.mutate();
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label="Delete task"
      title={`Delete ${task.title}`}
      disabled={deleteMutation.isPending}
      onClick={onDeleteTask}
    >
      <Trash2 className="h-4 w-4" aria-hidden="true" />
    </Button>
  );
}
