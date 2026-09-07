"use client";

import React, { createContext, useContext, useState, useCallback, useRef } from "react";

interface Toast {
  id: string;
  message: string;
  type: "error" | "success" | "warning" | "info";
}

interface ToastContextValue {
  addToast: (message: string, type?: Toast["type"]) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counterRef = useRef(0);

  const addToast = useCallback((message: string, type: Toast["type"] = "info") => {
    const id = `toast-${++counterRef.current}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const typeStyles: Record<Toast["type"], string> = {
    error: "bg-[#dc2626] text-white border-[#b91c1c]",
    success: "bg-[#22c55e] text-[#1e1e1e] border-[#16a34a]",
    warning: "bg-[#d99a4e] text-[#1e1e1e] border-[#b8803c]",
    info: "bg-[#1e1e1e] text-[#f4f0e6] border-[#333]",
  };

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div
        aria-live="assertive"
        aria-label="Notifications"
        className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="alert"
            className={`px-4 py-3 border-2 shadow-[3px_3px_0_0_rgba(0,0,0,0.2)] font-mono text-sm animate-in fade-in slide-in-from-bottom-2 duration-300 ${typeStyles[toast.type]}`}
          >
            <div className="flex items-start justify-between gap-3">
              <span>{toast.message}</span>
              <button
                onClick={() => removeToast(toast.id)}
                className="text-current opacity-60 hover:opacity-100 font-bold shrink-0"
                aria-label="Dismiss notification"
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
