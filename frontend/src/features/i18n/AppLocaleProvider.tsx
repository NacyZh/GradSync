import { type PropsWithChildren, useCallback, useEffect, useState } from 'react';

import { useAuth } from '../auth/AuthProvider';
import { I18nProvider, type Locale } from './I18nProvider';
import { useLocalePreference, useUpdateLocalePreference } from './api';
import { applyRuntimeLocalization } from './runtimeLocalization';

const LOCALE_STORAGE_KEY = 'gradsync.locale';

function initialLocale(): Locale {
  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
  if (stored === 'en' || stored === 'zh') return stored;
  return window.navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en';
}

export function AppLocaleProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const localeQuery = useLocalePreference({ enabled: Boolean(user) });
  const updateLocale = useUpdateLocalePreference();
  const [locale, setLocalLocale] = useState<Locale>(initialLocale);

  useEffect(() => {
    const remoteLocale = localeQuery.data?.locale;
    if (!user || !remoteLocale) return;
    setLocalLocale(remoteLocale);
    window.localStorage.setItem(LOCALE_STORAGE_KEY, remoteLocale);
  }, [localeQuery.data?.locale, user]);

  useEffect(() => {
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
    return applyRuntimeLocalization(locale);
  }, [locale]);

  const setLocale = useCallback((nextLocale: Locale) => {
    setLocalLocale(nextLocale);
    window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale);
    if (user) updateLocale.mutate(nextLocale);
  }, [updateLocale, user]);

  return <I18nProvider locale={locale} onLocaleChange={setLocale}>{children}</I18nProvider>;
}
