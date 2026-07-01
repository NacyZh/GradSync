import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

type BaseProps = {
  id: string;
  label: string;
  description?: string;
  error?: string;
  className?: string;
};

type InputFieldProps = BaseProps & InputHTMLAttributes<HTMLInputElement>;
type TextareaFieldProps = BaseProps & TextareaHTMLAttributes<HTMLTextAreaElement>;

export function FormField({ id, label, description, error, className, ...props }: InputFieldProps) {
  return (
    <div className={cn('grid gap-1.5', className)}>
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} aria-describedby={description ? `${id}-description` : undefined} aria-invalid={Boolean(error)} {...props} />
      {description ? <p id={`${id}-description`} className="text-xs text-muted-foreground">{description}</p> : null}
      {error ? <p className="text-xs font-bold text-destructive" role="alert">{error}</p> : null}
    </div>
  );
}

export function TextareaField({ id, label, description, error, className, ...props }: TextareaFieldProps) {
  return (
    <div className={cn('grid gap-1.5', className)}>
      <Label htmlFor={id}>{label}</Label>
      <Textarea id={id} aria-describedby={description ? `${id}-description` : undefined} aria-invalid={Boolean(error)} {...props} />
      {description ? <p id={`${id}-description`} className="text-xs text-muted-foreground">{description}</p> : null}
      {error ? <p className="text-xs font-bold text-destructive" role="alert">{error}</p> : null}
    </div>
  );
}

export function FieldGroup({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('grid gap-4', className)}>{children}</div>;
}
