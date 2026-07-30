import type { ReactNode } from "react";
import { X } from "lucide-react";

interface OverlayDrawerProps {
  title: string;
  isOpen: boolean;
  children?: ReactNode;
  onClose: () => void;
}

export function OverlayDrawer({ title, isOpen, children, onClose }: OverlayDrawerProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="overlay-backdrop" role="presentation">
      <aside className="overlay-drawer" aria-label={title} aria-modal="true" role="dialog">
        <div className="overlay-header">
          <h2>{title}</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close drawer">
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div className="overlay-body">{children}</div>
      </aside>
    </div>
  );
}
