import type { WarRoomEventResponse } from "./qualityWarRoomTypes";

export function AgentProgressTimeline({ events }: { events: WarRoomEventResponse[] }) {
  return (
    <ol className="agent-progress-timeline" data-testid="agent-progress-timeline">
      {events.map((event) => (
        <li key={event.id}>
          <strong>{event.event_type.replace(/_/g, " ")}</strong>
          <span>{event.concise_message}</span>
        </li>
      ))}
    </ol>
  );
}
