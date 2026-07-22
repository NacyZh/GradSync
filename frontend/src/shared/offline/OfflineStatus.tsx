import { WifiOff } from 'lucide-react';
import { useEffect, useState } from 'react';

import { useI18n } from '@/shared/i18n/I18nProvider';

export function OfflineStatus() {
  const [offline, setOffline] = useState(() => !window.navigator.onLine);
  const { t } = useI18n();

  useEffect(() => {
    const update = () => setOffline(!window.navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  if (!offline) return null;
  return (
    <div className="offline-status" role="status" aria-live="polite">
      <WifiOff className="h-4 w-4" aria-hidden="true" />
      <span><strong>{t('offlineMode')}</strong> {t('offlineDescription')}</span>
    </div>
  );
}
