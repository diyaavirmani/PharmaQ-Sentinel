import type { ReactNode } from "react";

interface ComplaintSectionProps {
  number: number;
  title: string;
  children: ReactNode;
}

export function ComplaintSection({ number, title, children }: ComplaintSectionProps) {
  return (
    <section className="complaint-section" aria-labelledby={`complaint-section-${number}`}>
      <div className="complaint-section__heading">
        <span className="complaint-section__number" aria-hidden="true">
          {number}.
        </span>
        <h2 id={`complaint-section-${number}`}>{title}</h2>
      </div>
      <div className="complaint-section__content">{children}</div>
    </section>
  );
}
