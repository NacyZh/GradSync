import type { PropsWithChildren } from 'react';

import { useAuth } from '../auth/AuthProvider';
import { I18nProvider } from './I18nProvider';
import { useLocalePreference } from './api';

export function AppLocaleProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const localeQuery = useLocalePreference({ enabled: Boolean(user) });
  const locale = user ? (localeQuery.data?.locale ?? 'en') : 'en';

  return <I18nProvider locale={locale}>{children}</I18nProvider>;
}
