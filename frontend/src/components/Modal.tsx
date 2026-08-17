import { useEffect } from "react";
import type { ReactNode } from "react";
import { XIcon } from "./icons";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}

export function Modal({ title, onClose, children, wide }: ModalProps) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-navy/50 lg:items-center lg:p-4"
      onClick={onClose}
    >
      <div
        className={`flex max-h-[90dvh] w-full flex-col overflow-y-auto rounded-t-lg border border-navy/10 bg-cream shadow-xl lg:max-h-none lg:overflow-visible lg:rounded-sm ${
          wide ? "lg:max-w-3xl" : "lg:max-w-lg"
        }`}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="sticky top-0 z-10 flex shrink-0 items-center justify-between border-b border-navy/10 bg-cream px-4 py-3">
          <h2 className="text-lg font-bold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm p-2 text-ink-soft hover:text-ink"
            aria-label="Cerrar"
          >
            <XIcon className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4 lg:max-h-[70vh] lg:overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}