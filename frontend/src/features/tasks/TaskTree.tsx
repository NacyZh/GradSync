export type TaskNode = {
  id: number;
  title: string;
  children?: TaskNode[];
};

export function TaskTree({ tasks }: { tasks: TaskNode[] }) {
  return (
    <ul>
      {tasks.map((task) => (
        <li key={task.id}>
          <span>{task.title}</span>
          {task.children && task.children.length > 0 ? <TaskTree tasks={task.children} /> : null}
        </li>
      ))}
    </ul>
  );
}
