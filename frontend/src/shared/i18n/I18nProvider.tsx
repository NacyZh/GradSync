import { createContext, type PropsWithChildren, useContext, useMemo } from 'react';

import { messagesEn } from '@/data/locale/messages.en';
import { messagesZh } from '@/data/locale/messages.zh';

type Messages = typeof messagesEn;
export type MessageKey = keyof Messages;
export type Locale = 'en' | 'zh';

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, params?: Record<string, string | number>) => string;
  formatDate: (value: string | number | Date, options?: Intl.DateTimeFormatOptions) => string;
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string;
};

function interpolate(message: string, params?: Record<string, string | number>) {
  if (!params) return message;
  return message.replace(/\{(\w+)\}/g, (match, key: string) => String(params[key] ?? match));
}

const I18nContext = createContext<I18nContextValue>({
  locale: 'en',
  setLocale: () => undefined,
  t: (key, params) => interpolate(messagesEn[key], params),
  formatDate: (value, options) => new Intl.DateTimeFormat('en', options).format(new Date(value)),
  formatNumber: (value, options) => new Intl.NumberFormat('en', options).format(value),
});

export function I18nProvider({
  locale = 'en',
  onLocaleChange = () => undefined,
  children,
}: PropsWithChildren<{ locale?: Locale; onLocaleChange?: (locale: Locale) => void }>) {
  const value = useMemo<I18nContextValue>(() => {
    const catalog = locale === 'zh' ? messagesZh : messagesEn;
    const intlLocale = locale === 'zh' ? 'zh-CN' : 'en';
    return {
      locale,
      setLocale: onLocaleChange,
      t: (key, params) => interpolate(catalog[key] ?? messagesEn[key], params),
      formatDate: (input, options) => new Intl.DateTimeFormat(intlLocale, options).format(new Date(input)),
      formatNumber: (input, options) => new Intl.NumberFormat(intlLocale, options).format(input),
    };
  }, [locale, onLocaleChange]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
