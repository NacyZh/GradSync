export function DuplicateAlert({ reason, message }: { reason?: string; message?: string }) {
  return (
    <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
      <strong>Duplicate</strong>
      <p>{message ?? `Matched existing paper by ${reason ?? 'metadata'}.`}</p>
    </div>
  );
}
