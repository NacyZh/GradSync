import { useI18n } from '@/shared/i18n/I18nProvider';
import { translateUiText } from '@/shared/i18n/translate';
import { PageShell } from '@/shared/ui/PageShell';

import { ProjectHealthDashboard } from './ProjectHealthDashboard';

export function ProjectHealthPage() {
  const { locale } = useI18n();
  const tr = (value: string) => translateUiText(value, locale);

  return (
    <PageShell
      title={tr('Project health operations')}
      description={tr('Prioritize intervention across projects without mixing operational monitoring with audit evidence.')}
    >
      <ProjectHealthDashboard />
    </PageShell>
  );
}
