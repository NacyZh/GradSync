export function UploadProgress({ label, value = 0 }: { label: string; value?: number }) {
  return (
    <div className="grid gap-2" role="status" aria-live="polite">
      <div className="flex items-center justify-between text-sm font-medium">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded bg-muted">
        <div className="h-full bg-primary transition-all" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
    </div>
  );
}

export const LocalImportProgress = UploadProgress;
