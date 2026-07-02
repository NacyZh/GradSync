import { createContext, type PropsWithChildren, useContext, useMemo } from 'react';

import { messagesEn } from './messages.en';
import { messagesZh } from './messages.zh';

type Messages = typeof messagesEn;
export type MessageKey = keyof Messages;
export type Locale = 'en' | 'zh';

type I18nContextValue = {
  locale: Locale;
  t: (key: MessageKey) => string;
};

const I18nContext = createContext<I18nContextValue>({ locale: 'en', t: (key) => messagesEn[key] });

export function I18nProvider({ locale = 'en', children }: PropsWithChildren<{ locale?: Locale }>) {
  const value = useMemo<I18nContextValue>(() => {
    const catalog = locale === 'zh' ? messagesZh : messagesEn;
    return {
      locale,
      t: (key) => catalog[key] ?? messagesEn[key],
    };
  }, [locale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
