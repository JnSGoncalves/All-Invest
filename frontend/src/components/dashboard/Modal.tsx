import { useEffect, useRef, type ReactNode } from "react";
import Icon from "./Icon";

interface ModalProps {
  title: string;
  description?: ReactNode;
  tone?: "default" | "danger";
  onClose: () => void;
  children: ReactNode;
}

// <dialog> nativo: foco preso no modal, Esc fecha e o fundo fica inerte.
export default function Modal({ title, description, tone = "default", onClose, children }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => dialog?.close();
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className={`modal modal-${tone}`}
      aria-labelledby="modal-title"
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
    >
      <div className="modal-body">
        <div className="modal-heading">
          <span className="modal-icon"><Icon name={tone === "danger" ? "trash" : "folder"} size={20} /></span>
          <div>
            <h2 id="modal-title">{title}</h2>
            {description && <p>{description}</p>}
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Fechar">
            <Icon name="close" size={18} />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
