import { ChevronDown } from "lucide-react";
import type { IntelligenceTab } from "../../features/complaint/complaintTypes";

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
  onExpandedChange: (isExpanded: boolean) => void;
  onActiveTabChange: (tab: IntelligenceTab) => void;
}

export function QualityIntelligenceDock({
  visible,
  isExpanded,
  activeTab,
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
              disabled
              onClick={() => onActiveTabChange(tabLabel)}
            >
              {tabLabel}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
