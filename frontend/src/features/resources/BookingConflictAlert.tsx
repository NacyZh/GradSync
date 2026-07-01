import { AlertTriangle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

type BookingConflictAlertProps = {
  message: string;
  title?: string;
};

export function BookingConflictAlert({ message, title = 'Booking conflict' }: BookingConflictAlertProps) {
  return (
    <Alert variant="warning" role="alert" className="border-warning/70 bg-warning/10 text-foreground">
      <AlertTriangle className="mr-2 inline h-4 w-4 text-warning" aria-hidden="true" />
      <AlertTitle className="inline">{title}</AlertTitle>
      <AlertDescription className="mt-2 text-muted-foreground">{message}</AlertDescription>
    </Alert>
  );
}
