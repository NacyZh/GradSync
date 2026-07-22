import { Languages } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';

import { useI18n } from './I18nProvider';

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n();
  const nextLocale = locale === 'zh' ? 'en' : 'zh';

  return (
    <Button
      variant="outline"
      type="button"
      onClick={() => setLocale(nextLocale)}
      aria-label={`${t('language')}: ${locale === 'zh' ? t('chinese') : t('english')}`}
    >
      <Languages className="h-4 w-4" aria-hidden="true" />
      {locale === 'zh' ? '中文' : 'EN'}
    </Button>
  );
}
