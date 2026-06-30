export type TaskNode = {
  id: number;
  title: string;
  status?: string;
  priority?: string;
  deadline_at?: string;
  assignee_id?: number;
  children?: TaskNode[];
};

function formatStatus(status?: string) {
  return (status ?? 'not_started').replaceAll('_', ' ');
}

export function TaskTree({ tasks, projectId }: { tasks: TaskNode[]; projectId?: number }) {
  return (
    <ul className="task-tree" aria-label="Task hierarchy">
      {tasks.map((task) => (
        <li key={task.id}>
          <details open>
            <summary>
              <span className="task-title">{task.title}</span>
              <span className={`status-pill ${task.status ?? 'not_started'}`}>{formatStatus(task.status)}</span>
              {task.deadline_at ? <time dateTime={task.deadline_at}>{new Date(task.deadline_at).toLocaleDateString()}</time> : null}
            </summary>
            <div className="task-meta">
              <span>Priority: {task.priority ?? 'normal'}</span>
              <span>Assignee: {task.assignee_id ? `User ${task.assignee_id}` : 'Unassigned'}</span>
              {projectId ? (
                <a href={`#task-${task.id}-status`} className="inline-action">
                  Update status
                </a>
              ) : null}
            </div>
            {task.children && task.children.length > 0 ? <TaskTree tasks={task.children} projectId={projectId} /> : null}
          </details>
        </li>
      ))}
    </ul>
  );
}
