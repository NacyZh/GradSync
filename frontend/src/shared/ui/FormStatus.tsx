type FormStatusProps = {
  error?: string;
  success?: string;
};

export function FormStatus({ error, success }: FormStatusProps) {
  if (error) {
    return <p role="alert">{error}</p>;
  }
  if (success) {
    return <p role="status">{success}</p>;
  }
  return null;
}
