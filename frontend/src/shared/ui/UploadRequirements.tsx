import { FileCheck2 } from 'lucide-react';

type UploadRequirementsProps = {
  title: string;
  extensions: string[];
  maxSizeLabel: string;
  description?: string;
};

export function UploadRequirements({ title, extensions, maxSizeLabel, description }: UploadRequirementsProps) {
  return (
    <div className="rounded-md border bg-muted/30 p-3 text-sm">
      <div className="mb-1 flex items-center gap-2 font-semibold">
        <FileCheck2 className="h-4 w-4" aria-hidden="true" />
        {title}
      </div>
      <p className="text-muted-foreground">
        {description ?? `${extensions.join(', ')} up to ${maxSizeLabel}`}
      </p>
    </div>
  );
}
