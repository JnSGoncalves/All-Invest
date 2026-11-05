import { useEffect, type CSSProperties } from "react";
import Icon from "./Icon";

export interface Toast {
  id: number;
  kind: "success" | "error" | "info";
  title: string;
  message?: string;
}

const DURATION_MS = { success: 6000, info: 6000, error: 10000 };

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const duration = DURATION_MS[toast.kind];

  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(toast.id), duration);
    return () => window.clearTimeout(timer);
  }, [duration, onDismiss, toast.id]);

  return (
    <div
      className={`toast toast-${toast.kind}`}
      role={toast.kind === "error" ? "alert" : "status"}
      style={{ "--toast-duration": `${duration}ms` } as CSSProperties}
    >
      <span className="toast-icon">
        <Icon name={toast.kind === "success" ? "check" : toast.kind === "error" ? "alert" : "info"} size={18} />
      </span>
      <div className="toast-copy">
        <strong>{toast.title}</strong>
        {toast.message && <span>{toast.message}</span>}
      </div>
      <button type="button" className="toast-close" onClick={() => onDismiss(toast.id)} aria-label="Fechar aviso">
        <Icon name="close" size={16} />
      </button>
      <span className="toast-progress" aria-hidden="true" />
    </div>
  );
}

export default function ToastViewport({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="toast-viewport" aria-live="polite">
      {toasts.map((toast) => <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />)}
    </div>
  );
}
