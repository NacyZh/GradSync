import { FileCheck2 } from 'lucide-react';

type UploadRequirementsProps = {
  title: string;
  extensions: string[];
  maxSizeLabel: string;
  description?: string;
};

export function UploadRequirements({ title, extensions, maxSizeLabel, description }: UploadRequirementsProps) {
  return (
    <div className="min-w-0 rounded-md border bg-muted/30 p-3 text-sm">
      <div className="mb-1 flex min-w-0 items-center gap-2 font-semibold">
        <FileCheck2 className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="min-w-0 break-words">{title}</span>
      </div>
      <p className="min-w-0 break-words text-muted-foreground">
        {description ?? `${extensions.join(', ')} up to ${maxSizeLabel}`}
      </p>
    </div>
  );
}
