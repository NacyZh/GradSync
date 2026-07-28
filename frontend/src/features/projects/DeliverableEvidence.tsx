import { ExternalLink, FileStack, Plus, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/primitives/select';
import { useI18n } from '@/shared/i18n/I18nProvider';

import type { ProjectMaterial } from './api';

export type EvidenceDraft = {
  type: 'project_material' | 'external_url';
  sourceId?: number;
  url?: string;
  label: string;
};

type Props = {
  materials: ProjectMaterial[];
  value: EvidenceDraft[];
  onChange: (value: EvidenceDraft[]) => void;
};

export function DeliverableEvidence({ materials, value, onChange }: Props) {
  const { t } = useI18n();
  const [type, setType] = useState<EvidenceDraft['type']>('project_material');
  const [query, setQuery] = useState('');
  const [selectedMaterial, setSelectedMaterial] = useState('');
  const [url, setUrl] = useState('');
  const [label, setLabel] = useState('');
  const filteredMaterials = useMemo(
    () =>
      materials.filter((material) =>
        (material.displayName ?? `${material.materialType} ${material.id}`)
          .toLowerCase()
          .includes(query.trim().toLowerCase()),
      ),
    [materials, query],
  );

  function addEvidence() {
    const normalizedLabel = label.trim();
    if (type === 'project_material' && selectedMaterial) {
      const material = materials.find((item) => item.id === selectedMaterial);
      onChange([
        ...value,
        {
          type,
          sourceId: Number(selectedMaterial),
          label:
            normalizedLabel ||
            material?.displayName ||
            `${material?.materialType ?? 'Material'} evidence`,
        },
      ]);
      setSelectedMaterial('');
    } else if (type === 'external_url' && url.trim()) {
      onChange([
        ...value,
        {
          type,
          url: url.trim(),
          label: normalizedLabel || 'External evidence',
        },
      ]);
      setUrl('');
    }
    setLabel('');
  }

  return (
    <section className="grid gap-3" aria-label="Submission evidence">
      <div className="grid gap-3 sm:grid-cols-[10rem_minmax(0,1fr)]">
        <Select value={type} onValueChange={(next) => setType(next as EvidenceDraft['type'])}>
          <SelectTrigger aria-label="Evidence type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="project_material">{t('projectMaterial')}</SelectItem>
            <SelectItem value="external_url">{t('externalHttpsLink')}</SelectItem>
          </SelectContent>
        </Select>
        {type === 'project_material' ? (
          <div className="grid gap-2">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t('searchProjectMaterials')}
              aria-label={t('searchProjectMaterials')}
            />
            <Select value={selectedMaterial} onValueChange={setSelectedMaterial}>
              <SelectTrigger aria-label={t('selectProjectMaterial')}>
                <SelectValue placeholder={t('selectMaterial')} />
              </SelectTrigger>
              <SelectContent>
                {filteredMaterials.map((material) => (
                  <SelectItem key={material.id} value={material.id}>
                    {material.displayName ?? `${material.materialType} ${material.id}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ) : (
          <Input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            type="url"
            placeholder="https://"
            aria-label="External evidence URL"
          />
        )}
      </div>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          placeholder={t('evidenceLabel')}
          aria-label={t('evidenceLabel')}
        />
        <Button
          type="button"
          variant="outline"
          onClick={addEvidence}
          disabled={
            type === 'project_material' ? !selectedMaterial : !url.trim()
          }
        >
          <Plus className="h-4 w-4" />
          {t('addEvidence')}
        </Button>
      </div>
      {value.length ? (
        <ul className="grid gap-2">
          {value.map((item, index) => (
            <li
              key={`${item.type}-${item.sourceId ?? item.url}-${index}`}
              className="flex min-w-0 items-center gap-2 rounded-md border px-3 py-2 text-sm"
            >
              {item.type === 'project_material' ? (
                <FileStack className="h-4 w-4 shrink-0" />
              ) : (
                <ExternalLink className="h-4 w-4 shrink-0" />
              )}
              <span className="min-w-0 flex-1 truncate">{item.label}</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Remove ${item.label}`}
                onClick={() => onChange(value.filter((_, itemIndex) => itemIndex !== index))}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          {t('evidenceRequiredMessage')}
        </p>
      )}
    </section>
  );
}
