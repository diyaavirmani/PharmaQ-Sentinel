import clsx from "clsx";

type StatusBadgeTone = "neutral" | "purple" | "success" | "warning" | "danger";

interface StatusBadgeProps {
  children: string;
  tone?: StatusBadgeTone;
}

export function StatusBadge({ children, tone = "neutral" }: StatusBadgeProps) {
  return <span className={clsx("status-badge", `status-badge--${tone}`)}>{children}</span>;
}
