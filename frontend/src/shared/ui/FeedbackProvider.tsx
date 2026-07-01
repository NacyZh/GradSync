import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { PropsWithChildren, ReactNode } from 'react';

import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from '@/components/ui/toast';
import { TooltipProvider } from '@/components/ui/tooltip';

import { ConfirmDialog } from './ConfirmDialog';

type ToastTone = 'success' | 'error' | 'info';

type ToastMessage = {
  id: number;
  message: string;
  tone: ToastTone;
};

type ConfirmState = {
  title: string;
  message: string;
  actionLabel: string;
  resolve: (confirmed: boolean) => void;
};

type Theme = 'light' | 'dark';

type FeedbackContextValue = {
  notify: (message: string, tone?: ToastTone) => void;
  confirm: (options: Omit<ConfirmState, 'resolve'>) => Promise<boolean>;
  theme: Theme;
  toggleTheme: () => void;
};

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'light';
  const stored = window.localStorage.getItem('gradsync-theme');
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function FeedbackProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.classList.toggle('dark', theme === 'dark');
    window.localStorage.setItem('gradsync-theme', theme);
  }, [theme]);

  const notify = useCallback((message: string, tone: ToastTone = 'info') => {
    const id = Date.now();
    setToasts((items) => [...items, { id, message, tone }]);
  }, []);

  const confirm = useCallback((options: Omit<ConfirmState, 'resolve'>) => {
    return new Promise<boolean>((resolve) => {
      setConfirmState({ ...options, resolve });
    });
  }, []);

  const value = useMemo<FeedbackContextValue>(
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
    <FeedbackContext.Provider value={value}>
      <TooltipProvider delayDuration={250}>
        <ToastProvider swipeDirection="right">
          {children}
          {toasts.map((toast) => (
            <Toast
              key={toast.id}
              open
              variant={toast.tone === 'error' ? 'destructive' : toast.tone === 'success' ? 'success' : 'default'}
              onOpenChange={(open) => {
                if (!open) {
                  setToasts((items) => items.filter((item) => item.id !== toast.id));
                }
              }}
            >
              <div className="grid gap-1">
                <ToastTitle>{toast.tone === 'error' ? 'Action failed' : toast.tone === 'success' ? 'Action complete' : 'GradSync'}</ToastTitle>
                <ToastDescription>{toast.message}</ToastDescription>
              </div>
              <ToastClose aria-label="Dismiss notification" />
            </Toast>
          ))}
          <ToastViewport aria-label="Notifications" />
          {confirmState ? (
            <ConfirmDialog
              open
              title={confirmState.title}
              message={confirmState.message}
              actionLabel={confirmState.actionLabel}
              onConfirm={() => closeConfirm(true)}
              onCancel={() => closeConfirm(false)}
            />
          ) : null}
        </ToastProvider>
      </TooltipProvider>
    </FeedbackContext.Provider>
  );
}

export function useFeedback() {
  const context = useContext(FeedbackContext);
  if (!context) {
    throw new Error('useFeedback must be used within FeedbackProvider');
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
  return <span className="text-xs text-muted-foreground">{children}</span>;
}
