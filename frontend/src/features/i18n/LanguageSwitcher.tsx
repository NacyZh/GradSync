import { Languages } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';

import { useLocalePreference, useUpdateLocalePreference, type Locale } from './api';
import { useI18n } from './I18nProvider';

export function LanguageSwitcher() {
  const localeQuery = useLocalePreference();
  const updateLocale = useUpdateLocalePreference();
  const { t } = useI18n();
  const locale = localeQuery.data?.locale ?? 'en';
  const nextLocale: Locale = locale === 'zh' ? 'en' : 'zh';

  return (
    <Button
      variant="outline"
      type="button"
      onClick={() => updateLocale.mutate(nextLocale)}
      disabled={updateLocale.isPending}
      aria-label={`${t('language')}: ${locale === 'zh' ? t('chinese') : t('english')}`}
    >
      <Languages className="h-4 w-4" aria-hidden="true" />
      {locale === 'zh' ? '中文' : 'EN'}
    </Button>
  );
}
