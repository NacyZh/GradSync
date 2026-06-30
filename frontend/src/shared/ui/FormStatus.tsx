type FormStatusProps = {
  error?: string;
  success?: string;
  className?: string;
};

export function FormStatus({ error, success, className = '' }: FormStatusProps) {
  if (error) {
    return <p className={`form-status error ${className}`} role="alert">{error}</p>;
  }
  if (success) {
    return <p className={`form-status success ${className}`} role="status">{success}</p>;
  }
  return null;
}
