import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle2, AlertTriangle, AlertCircle, Info } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  title?: string;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  toast: (message: string, type?: ToastType, title?: string) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((message: string, type: ToastType = 'info', title?: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type, title }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  }, [removeToast]);

  const success = useCallback((message: string, title?: string) => toast(message, 'success', title), [toast]);
  const error = useCallback((message: string, title?: string) => toast(message, 'error', title), [toast]);
  const warning = useCallback((message: string, title?: string) => toast(message, 'warning', title), [toast]);
  const info = useCallback((message: string, title?: string) => toast(message, 'info', title), [toast]);

  return (
    <ToastContext.Provider value={{ toast, success, error, warning, info }}>
      {children}
      {/* Toast Render Viewport */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((t) => {
          const borderStyle =
            t.type === 'success'
              ? 'border-emerald-500/30'
              : t.type === 'error'
              ? 'border-rose-500/30'
              : t.type === 'warning'
              ? 'border-amber-500/30'
              : 'border-zinc-800';

          const icon =
            t.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            ) : t.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            ) : t.type === 'warning' ? (
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            ) : (
              <Info className="w-4 h-4 text-zinc-400 shrink-0 mt-0.5" />
            );

          return (
            <div
              key={t.id}
              className={`pointer-events-auto bg-zinc-950/95 backdrop-blur-sm border ${borderStyle} rounded-lg p-3.5 shadow-2xl transition-all duration-200 animate-in fade-in slide-in-from-bottom-2`}
            >
              <div className="flex items-start gap-3">
                {icon}
                <div className="flex-1 min-w-0">
                  {t.title && (
                    <div className="text-xs font-medium text-zinc-200 mb-0.5">
                      {t.title}
                    </div>
                  )}
                  <div className="text-xs text-zinc-400 leading-relaxed break-words font-mono">
                    {t.message}
                  </div>
                </div>
                <button
                  onClick={() => removeToast(t.id)}
                  className="text-zinc-500 hover:text-zinc-300 transition-colors p-0.5"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
