import { AsyncState } from '../../shared/ui/AsyncState';

export function ProjectEmptyState() {
  return <AsyncState state="empty" message="No project records are available in this project." />;
}
