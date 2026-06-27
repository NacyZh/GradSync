type AsyncStateProps = {
  state: 'loading' | 'empty' | 'error' | 'success';
  message: string;
};

export function AsyncState({ state, message }: AsyncStateProps) {
  return (
    <section role={state === 'error' ? 'alert' : 'status'} data-state={state}>
      <p>{message}</p>
    </section>
  );
}
