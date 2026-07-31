import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { BatchImpactPanel } from "../../features/batchImpact/BatchImpactPanel";
import type { IntelligenceTab, TimelineEntryResponse } from "../../features/complaint/complaintTypes";
import { InvestigationSupportPanel } from "../../features/investigationSupport/InvestigationSupportPanel";
import type { DuplicateAnalysisResult, InvestigationPlaybookResult } from "../../features/investigationSupport/investigationSupportTypes";
import { QualityWarRoomPanel } from "../../features/qualityWarRoom/QualityWarRoomPanel";
import { InspectionBriefActions } from "../../features/reports/InspectionBriefActions";

const intelligenceTabs: IntelligenceTab[] = [
  "Batch Intelligence",
  "Quality War Room",
  "Evidence & Audit",
  "Investigation Support"
];

interface QualityIntelligenceDockProps {
  visible: boolean;
  isExpanded: boolean;
  activeTab: IntelligenceTab;
  draftId?: string | null;
  complaintId?: string | null;
  batchNumber?: string | null;
  timeline?: TimelineEntryResponse[];
  duplicateAnalysis?: DuplicateAnalysisResult | null;
  investigationPlaybook?: InvestigationPlaybookResult | null;
  onDuplicateAnalysisComplete?: (result: DuplicateAnalysisResult) => void;
  onInvestigationPlaybookComplete?: (result: InvestigationPlaybookResult) => void;
  onExpandedChange: (isExpanded: boolean) => void;
  onActiveTabChange: (tab: IntelligenceTab) => void;
}

function valueText(value: unknown): string {
  if (value === null || value === undefined) {
    return "Not provided";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function InspectorReplay({ timeline = [] }: { timeline?: TimelineEntryResponse[] }) {
  const [actorFilter, setActorFilter] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [fieldFilter, setFieldFilter] = useState("");
  const actors = useMemo(() => Array.from(new Set(timeline.map((entry) => entry.actor))).sort(), [timeline]);
  const eventTypes = useMemo(() => Array.from(new Set(timeline.map((entry) => entry.event_type))).sort(), [timeline]);
  const fields = useMemo(
    () => Array.from(new Set(timeline.flatMap((entry) => entry.affected_fields))).sort(),
    [timeline]
  );
  const filteredTimeline = timeline.filter((entry) => {
    if (actorFilter && entry.actor !== actorFilter) {
      return false;
    }
    if (eventTypeFilter && entry.event_type !== eventTypeFilter) {
      return false;
    }
    if (fieldFilter && !entry.affected_fields.includes(fieldFilter)) {
      return false;
    }
    return true;
  });

  return (
    <div className="inspector-replay" data-testid="inspector-replay">
      <div className="inspector-replay__filters" aria-label="Inspector Replay filters">
        <label>
          Actor
          <select value={actorFilter} onChange={(event) => setActorFilter(event.target.value)}>
            <option value="">All actors</option>
            {actors.map((actor) => (
              <option key={actor} value={actor}>{actor}</option>
            ))}
          </select>
        </label>
        <label>
          Event type
          <select value={eventTypeFilter} onChange={(event) => setEventTypeFilter(event.target.value)}>
            <option value="">All events</option>
            {eventTypes.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </label>
        <label>
          Field
          <select value={fieldFilter} onChange={(event) => setFieldFilter(event.target.value)}>
            <option value="">All fields</option>
            {fields.map((field) => (
              <option key={field} value={field}>{field}</option>
            ))}
          </select>
        </label>
      </div>
      {filteredTimeline.length ? (
        <ol className="inspector-replay__timeline">
          {filteredTimeline.map((entry) => (
            <li key={entry.event_id}>
              <div>
                <strong>{entry.title}</strong>
                <span>{entry.actor} - {entry.timestamp}</span>
              </div>
              <p>{entry.description}</p>
              {entry.affected_fields.length ? <span>Fields: {entry.affected_fields.join(", ")}</span> : null}
              {entry.old_value || entry.new_value ? (
                <code>{valueText({ old: entry.old_value, new: entry.new_value })}</code>
              ) : null}
              {entry.evidence_references.length ? <button type="button">Jump to evidence</button> : null}
              {entry.attachment_references.length ? <span>Attachments: {entry.attachment_references.length}</span> : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="inspector-replay__empty">Evidence and audit events will appear here after complaint fields are populated.</p>
      )}
    </div>
  );
}

export function QualityIntelligenceDock({
  visible,
  isExpanded,
  activeTab,
  draftId = null,
  complaintId = null,
  batchNumber = null,
  timeline,
  duplicateAnalysis = null,
  investigationPlaybook = null,
  onDuplicateAnalysisComplete,
  onInvestigationPlaybookComplete,
  onExpandedChange,
  onActiveTabChange
}: QualityIntelligenceDockProps) {
  if (!visible) {
    return null;
  }

  return (
    <section className="quality-intelligence-dock" data-testid="quality-intelligence-dock">
      <button
        type="button"
        className="quality-intelligence-dock__trigger"
        aria-expanded={isExpanded}
        onClick={() => onExpandedChange(!isExpanded)}
      >
        <span>Quality Intelligence</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>

      {isExpanded ? (
        <div className="quality-intelligence-dock__tabs" role="tablist" aria-label="Quality Intelligence">
          {intelligenceTabs.map((tabLabel) => (
            <button
              key={tabLabel}
              type="button"
              role="tab"
              aria-selected={activeTab === tabLabel}
              onClick={() => onActiveTabChange(tabLabel)}
            >
              {tabLabel}
            </button>
          ))}
        </div>
      ) : null}
      {isExpanded && activeTab === "Batch Intelligence" ? (
        <div className="quality-intelligence-dock__panel">
          <BatchImpactPanel draftId={draftId} batchNumber={batchNumber} />
        </div>
      ) : null}
      {isExpanded && activeTab === "Evidence & Audit" ? (
        <div className="quality-intelligence-dock__panel">
          <InspectionBriefActions complaintId={complaintId} />
          <InspectorReplay timeline={timeline} />
        </div>
      ) : null}
      {isExpanded && activeTab === "Quality War Room" ? (
        <div className="quality-intelligence-dock__panel">
          <QualityWarRoomPanel draftId={draftId} />
        </div>
      ) : null}
      {isExpanded && activeTab === "Investigation Support" ? (
        <div className="quality-intelligence-dock__panel">
          <InvestigationSupportPanel
            draftId={draftId}
            duplicateAnalysis={duplicateAnalysis}
            playbook={investigationPlaybook}
            onDuplicateAnalysisComplete={(result) => onDuplicateAnalysisComplete?.(result)}
            onPlaybookComplete={(result) => onInvestigationPlaybookComplete?.(result)}
          />
        </div>
      ) : null}
    </section>
  );
}
