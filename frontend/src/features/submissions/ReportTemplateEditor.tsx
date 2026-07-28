import { ArrowDown, ArrowUp, Plus, Send } from 'lucide-react';
import { useState } from 'react';

import { useI18n } from '@/shared/i18n/I18nProvider';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { useAppFeedback } from '@/shared/ui/AppFeedback';

import {
  type ReportTemplateField,
  type ReportTemplateVersion,
  publishReportTemplate,
  updateReportTemplate,
} from './api';

export function ReportTemplateEditor({
  projectId,
  template,
  onChanged,
}: {
  projectId: number;
  template: ReportTemplateVersion;
  onChanged: () => void;
}) {
  const { t } = useI18n();
  const { notify, confirm } = useAppFeedback();
  const [fields, setFields] = useState(template.fields);
  const [pending, setPending] = useState(false);
  const editable = template.status === 'draft';

  function move(index: number, offset: number) {
    const target = index + offset;
    if (target < 0 || target >= fields.length) return;
    const next = [...fields];
    [next[index], next[target]] = [next[target], next[index]];
    setFields(next.map((field, order) => ({ ...field, order })));
  }

  function addField() {
    const order = fields.length;
    setFields([
      ...fields,
      {
        id: -Date.now(),
        key: `field_${order + 1}`,
        labelEn: '',
        labelZh: '',
        fieldType: 'long_text',
        required: false,
        order,
        options: [],
        analyticsEnabled: false,
      },
    ]);
  }

  async function save() {
    setPending(true);
    try {
      await updateReportTemplate(projectId, template, fields);
      notify(t('reportTemplateSaved'), 'success');
      onChanged();
    } catch (error) {
      notify(error instanceof Error ? error.message : t('reportTemplateSaveFailed'), 'error');
    } finally {
      setPending(false);
    }
  }

  async function publish() {
    const accepted = await confirm({
      title: t('publishReportTemplate'),
      message: t('publishTemplatePeriodLock'),
      actionLabel: t('publish'),
    });
    if (!accepted) return;
    setPending(true);
    try {
      await publishReportTemplate(projectId, template);
      notify(t('reportTemplatePublished'), 'success');
      onChanged();
    } catch (error) {
      notify(error instanceof Error ? error.message : t('reportTemplatePublishFailed'), 'error');
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="grid gap-3" aria-label={t('reportTemplateEditor')}>
      <div className="max-h-[34rem] space-y-2 overflow-y-auto pr-1">
        {fields.map((field, index) => (
          <div key={field.id} className="grid gap-2 rounded-md border p-3 lg:grid-cols-[auto_1fr_1fr_11rem] lg:items-end">
            <div className="flex gap-1">
              <Button type="button" size="icon" variant="ghost" disabled={!editable || index === 0} title={t('moveUp')} onClick={() => move(index, -1)}>
                <ArrowUp className="h-4 w-4" />
              </Button>
              <Button type="button" size="icon" variant="ghost" disabled={!editable || index === fields.length - 1} title={t('moveDown')} onClick={() => move(index, 1)}>
                <ArrowDown className="h-4 w-4" />
              </Button>
            </div>
            <label className="grid gap-1 text-sm font-medium">
              {t('englishLabel')}
              <Input disabled={!editable} value={field.labelEn} onChange={(event) => setFields((current) => current.map((item) => item.id === field.id ? { ...item, labelEn: event.target.value } : item))} />
            </label>
            <label className="grid gap-1 text-sm font-medium">
              {t('chineseLabel')}
              <Input disabled={!editable} value={field.labelZh} onChange={(event) => setFields((current) => current.map((item) => item.id === field.id ? { ...item, labelZh: event.target.value } : item))} />
            </label>
            <label className="grid gap-1 text-sm font-medium">
              {t('fieldType')}
              <select className="h-10 rounded-md border bg-background px-3" disabled={!editable} value={field.fieldType} onChange={(event) => setFields((current) => current.map((item) => item.id === field.id ? { ...item, fieldType: event.target.value as ReportTemplateField['fieldType'] } : item))}>
                <option value="long_text">{t('longText')}</option>
                <option value="number">{t('number')}</option>
                <option value="percentage">{t('percentage')}</option>
                <option value="single_choice">{t('singleChoice')}</option>
                <option value="multiple_choice">{t('multipleChoice')}</option>
                <option value="execution_progress">{t('executionProgress')}</option>
                <option value="risk_blocker">{t('riskBlocker')}</option>
              </select>
            </label>
          </div>
        ))}
      </div>
      {editable ? (
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={addField}><Plus className="h-4 w-4" />{t('addField')}</Button>
          <Button type="button" disabled={pending} onClick={save}>{t('save')}</Button>
          <Button type="button" variant="secondary" disabled={pending} onClick={publish}><Send className="h-4 w-4" />{t('publish')}</Button>
        </div>
      ) : null}
    </section>
  );
}
