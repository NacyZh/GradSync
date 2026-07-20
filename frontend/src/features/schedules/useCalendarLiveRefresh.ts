import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';

import { listCalendarEvents } from './api';

export function useCalendarLiveRefresh(enabled: boolean) {
  const queryClient = useQueryClient();
  const cursor = useRef<string>();
  const [isStale, setIsStale] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const page = await listCalendarEvents(cursor.current);
      cursor.current = page.latestEventId || cursor.current;
      if (page.results.length) {
        await queryClient.invalidateQueries({ queryKey: ['calendar'] });
      }
      setIsStale(false);
    } catch {
      setIsStale(true);
    }
  }, [queryClient]);

  useEffect(() => {
    if (!enabled) return undefined;
    const timer = window.setInterval(() => { void refresh(); }, 5000);
    return () => window.clearInterval(timer);
  }, [enabled, refresh]);

  return { isStale, retry: refresh };
}
