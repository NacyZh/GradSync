import { useCallback, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { listProjectEvents } from './api';

export function useProjectLiveRefresh(projectId: number | null | undefined, latestEventId?: string | null) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<'fresh' | 'refreshing' | 'stale'>('fresh');

  const invalidateProjectQueries = useCallback(() => {
    if (!projectId) return;
    queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    queryClient.invalidateQueries({ queryKey: ['projectMaterials', projectId] });
    queryClient.invalidateQueries({ queryKey: ['projects'] });
  }, [projectId, queryClient]);

  useEffect(() => {
    if (!projectId) return undefined;
    let cancelled = false;
    let after = latestEventId ?? null;

    const refresh = async () => {
      setState('refreshing');
      try {
        const payload = await listProjectEvents(projectId, after);
        if (cancelled) return;
        if (payload.results.length === 0) {
          setState('fresh');
          return;
        }
        after = payload.results[0]?.id ?? after;
        invalidateProjectQueries();
        setState('fresh');
      } catch {
        setState('stale');
      }
    };

    window.addEventListener('focus', refresh);
    const interval = window.setInterval(refresh, 5_000);
    return () => {
      cancelled = true;
      window.removeEventListener('focus', refresh);
      window.clearInterval(interval);
    };
  }, [invalidateProjectQueries, latestEventId, projectId]);

  return { state, refresh: invalidateProjectQueries };
}
