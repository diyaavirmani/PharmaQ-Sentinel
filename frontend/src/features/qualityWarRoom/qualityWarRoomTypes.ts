export interface WarRoomEventResponse {
  id: string;
  run_id: string;
  event_type: string;
  agent_name: string | null;
  status: string;
  concise_message: string;
  evidence_ids_json: { evidence_ids?: string[] } | null;
  created_at: string;
}

export interface SpecialistOutput {
  agent_name: string;
  status: "COMPLETE" | "FAILED" | "UNAVAILABLE";
  concise_findings: string[];
  evidence_ids: string[];
  hypotheses: string[];
  recommended_checks: string[];
  immediate_considerations: string[];
  open_questions: string[];
  contradictions: string[];
  confidence: string;
  limitations: string[];
}

export interface QualityWarRoomRunResponse {
  id: string;
  draft_id: string;
  status: string;
  iteration_count: number;
  specialist_outputs_json: Record<string, SpecialistOutput>;
  auditor_output_json: {
    accepted_findings: string[];
    challenged_findings: string[];
    rejected_claims: string[];
    missing_evidence: string[];
    contradiction_findings: string[];
    specialist_revision_requests: Record<string, string[]>;
    compliance_warnings: string[];
  };
  consensus_json: {
    suggested_severity: string;
    suggested_priority: string;
    recommended_routes: string[];
    immediate_containment_considerations: string[];
    investigation_priorities: string[];
    root_cause_hypotheses: string[];
    confirmation_tests: string[];
    CAPA_considerations: Record<string, string[]>;
    agent_agreements: string[];
    agent_disagreements: string[];
    rejected_unsupported_claims: string[];
    unresolved_questions: string[];
    evidence_ids: string[];
    limitations: string[];
    human_approval_required: boolean;
  };
  started_at: string;
  completed_at: string | null;
  error_summary: string | null;
  events: WarRoomEventResponse[];
}

export interface QualityWarRoomRunStartedResponse {
  run_id: string;
  status: string;
}
