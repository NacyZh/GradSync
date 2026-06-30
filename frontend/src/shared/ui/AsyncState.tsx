type AsyncStateProps = {
  state: 'loading' | 'empty' | 'error' | 'success';
  message: string;
  action?: React.ReactNode;
};

export function AsyncState({ state, message, action }: AsyncStateProps) {
  return (
    <section className={`async-state ${state}`} role={state === 'error' ? 'alert' : 'status'} data-state={state}>
      {state === 'loading' ? (
        <div aria-hidden="true" className="skeleton-stack">
          <span />
          <span />
          <span />
        </div>
      ) : null}
      {state === 'empty' ? <div aria-hidden="true" className="empty-illustration">GS</div> : null}
      <p>{message}</p>
      {action ? <div className="async-action">{action}</div> : null}
    </section>
  );
}
