import { AsyncState } from '../../shared/ui/AsyncState';

export function TaskEmptyState() {
  return <AsyncState state="empty" message="No tasks are defined for this project." />;
}
