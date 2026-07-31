export interface DuplicateCandidateResult {
  candidate_complaint_id: string;
  complaint_number: string;
  classification: string;
  total_score: number;
  reasons: string[];
  matching_fields: string[];
  contradicting_fields: string[];
  evidence_references: string[];
  date_distance_days: number | null;
  text_similarity: string;
  recommended_user_action: string;
}

export interface RecurrenceSignal {
  signal_type: string;
  description: string;
  evidence_references: string[];
  limitation: string;
}

export interface DuplicateAnalysisResult {
  run_id: string;
  draft_id: string;
  candidates: DuplicateCandidateResult[];
  recurrence_signals: RecurrenceSignal[];
  limitations: string[];
}

export interface PlaybookStep {
  id: string;
  title: string;
  rationale: string;
  evidence_references: string[];
  owner_hint: string;
  limitation: string;
}

export interface InvestigationPlaybookResult {
  run_id: string;
  draft_id: string;
  category: string;
  immediate_containment: PlaybookStep[];
  investigation_checklist: PlaybookStep[];
  root_cause_hypotheses: PlaybookStep[];
  CAPA_considerations: Record<string, PlaybookStep[]>;
  limitations: string[];
}
