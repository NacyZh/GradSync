import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { PropsWithChildren, ReactNode } from 'react';

type Toast = {
  id: number;
  message: string;
  tone: 'success' | 'error' | 'info';
};

type ConfirmState = {
  title: string;
  message: string;
  actionLabel: string;
  resolve: (confirmed: boolean) => void;
};

type Theme = 'light' | 'dark';

type AppFeedbackContextValue = {
  notify: (message: string, tone?: Toast['tone']) => void;
  confirm: (options: Omit<ConfirmState, 'resolve'>) => Promise<boolean>;
  theme: Theme;
  toggleTheme: () => void;
};

const AppFeedbackContext = createContext<AppFeedbackContextValue | null>(null);

function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'light';
  const stored = window.localStorage.getItem('gradsync-theme');
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function AppFeedbackProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('gradsync-theme', theme);
  }, [theme]);

  const notify = useCallback((message: string, tone: Toast['tone'] = 'info') => {
    const id = Date.now();
    setToasts((items) => [...items, { id, message, tone }]);
    window.setTimeout(() => {
      setToasts((items) => items.filter((toast) => toast.id !== id));
    }, 3500);
  }, []);

  const confirm = useCallback((options: Omit<ConfirmState, 'resolve'>) => {
    return new Promise<boolean>((resolve) => {
      setConfirmState({ ...options, resolve });
    });
  }, []);

  const value = useMemo<AppFeedbackContextValue>(
    () => ({
      notify,
      confirm,
      theme,
      toggleTheme: () => setTheme((current) => (current === 'dark' ? 'light' : 'dark')),
    }),
    [confirm, notify, theme],
  );

  function closeConfirm(confirmed: boolean) {
    confirmState?.resolve(confirmed);
    setConfirmState(null);
  }

  return (
    <AppFeedbackContext.Provider value={value}>
      {children}
      <div className="toast-region" aria-live="polite" aria-label="Notifications">
        {toasts.map((toast) => (
          <div className={`toast ${toast.tone}`} key={toast.id} role="status">
            {toast.message}
          </div>
        ))}
      </div>
      {confirmState ? (
        <div className="dialog-backdrop" role="presentation">
          <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title">
            <h2 id="confirm-dialog-title">{confirmState.title}</h2>
            <p>{confirmState.message}</p>
            <div className="action-row">
              <button className="button danger" type="button" onClick={() => closeConfirm(true)}>
                {confirmState.actionLabel}
              </button>
              <button className="button" type="button" onClick={() => closeConfirm(false)}>
                Cancel
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </AppFeedbackContext.Provider>
  );
}

export function useAppFeedback() {
  const context = useContext(AppFeedbackContext);
  if (!context) {
    throw new Error('useAppFeedback must be used within AppFeedbackProvider');
  }
  return context;
}

export function useSubmitShortcut(callback: () => void, enabled = true) {
  useEffect(() => {
    if (!enabled) return undefined;

    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        callback();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        callback();
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [callback, enabled]);
}

export function KeyboardHint({ children }: { children: ReactNode }) {
  return <span className="keyboard-hint">{children}</span>;
}
