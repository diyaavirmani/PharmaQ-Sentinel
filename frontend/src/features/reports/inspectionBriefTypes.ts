export interface InspectionBriefField {
  label: string;
  value: unknown;
}

export interface InspectionBriefSection {
  title: string;
  fields: InspectionBriefField[];
  rows: Record<string, unknown>[];
  notes: string[];
}

export interface InspectionBrief {
  report_id: string;
  title: string;
  disclaimer: string;
  complaint_id: string;
  complaint_number: string;
  version_number: number;
  document_identifier: string;
  generated_at: string;
  snapshot_checksum: string;
  report_checksum: string;
  sections: InspectionBriefSection[];
  limitations: string[];
}
