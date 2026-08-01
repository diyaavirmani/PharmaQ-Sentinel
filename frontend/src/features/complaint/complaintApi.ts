import { createApi, type BaseQueryFn } from "@reduxjs/toolkit/query/react";
import { getApiBaseUrl } from "../../services/apiClient";
import type {
  BatchImpactResponse,
  ContainmentSimulationRequest,
  ContainmentSimulationResponse
} from "../batchImpact/batchImpactTypes";
import type {
  DuplicateAnalysisResult,
  InvestigationPlaybookResult
} from "../investigationSupport/investigationSupportTypes";
import type { InspectionBrief } from "../reports/inspectionBriefTypes";
import type {
  QualityWarRoomRunResponse,
  QualityWarRoomRunStartedResponse
} from "../qualityWarRoom/qualityWarRoomTypes";
import type {
  ComplaintDraftResponse,
  ComplaintDraftStatusResponse,
  ComplaintAttachmentStatusResponse,
  ComplaintAttachmentUploadResponse,
  ComplaintLedgerListResponse,
  ComplaintMessageListResponse,
  ComplaintResponse,
  CreateComplaintDraftRequest,
  DevelopmentPatchRequest,
  FieldEvidenceDetailResponse,
  FieldEvidenceListResponse,
  SaveComplaintRequest,
  SendComplaintMessageRequest,
  SendComplaintMessageResponse,
  TimelineListResponse
} from "./complaintTypes";

export interface ComplaintBaseQueryArgs {
  url: string;
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
}

export interface ComplaintBaseQueryError {
  status: number | "FETCH_ERROR";
  data: unknown;
}

const complaintBaseQuery: BaseQueryFn<
  string | ComplaintBaseQueryArgs,
  unknown,
  ComplaintBaseQueryError
> = async (args, api) => {
  const request = typeof args === "string" ? { url: args, method: "GET" as const } : args;
  const headers = new Headers({ Accept: "application/json" });
  const init: RequestInit = {
    method: request.method ?? "GET",
    headers,
    signal: api.signal
  };

  if (request.body !== undefined) {
    if (request.body instanceof FormData) {
      init.body = request.body;
    } else {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(request.body);
    }
  }

  try {
    const response = await fetch(`${getApiBaseUrl()}${request.url}`, init);
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      return { error: { status: response.status, data } };
    }
    return { data };
  } catch (error) {
    return {
      error: {
        status: "FETCH_ERROR",
        data: error instanceof Error ? error.message : "Network request failed"
      }
    };
  }
};

export const complaintApi = createApi({
  reducerPath: "complaintApi",
  baseQuery: complaintBaseQuery,
  tagTypes: [
    "ComplaintDraft",
    "ComplaintMessage",
    "ComplaintAttachment",
    "ComplaintEvidence",
    "ComplaintTimeline",
    "ComplaintLedger",
    "BatchImpact",
    "QualityWarRoom",
    "InvestigationSupport",
    "InspectionBrief"
  ],
  endpoints: (builder) => ({
    createComplaintDraft: builder.mutation<ComplaintDraftResponse, CreateComplaintDraftRequest>({
      query: (body) => ({
        url: "/complaint-drafts",
        method: "POST",
        body
      }),
      invalidatesTags: (_result, _error, _arg) => [{ type: "ComplaintDraft", id: "ACTIVE" }]
    }),
    getComplaintDraft: builder.query<ComplaintDraftResponse, string>({
      query: (draftId) => `/complaint-drafts/${draftId}`,
      providesTags: (_result, _error, draftId) => [{ type: "ComplaintDraft", id: draftId }]
    }),
    resetComplaintDraft: builder.mutation<ComplaintDraftResponse, string>({
      query: (draftId) => ({
        url: `/complaint-drafts/${draftId}/reset`,
        method: "POST"
      }),
      invalidatesTags: (_result, _error, draftId) => [
        { type: "ComplaintDraft", id: draftId },
        { type: "ComplaintDraft", id: "ACTIVE" },
        { type: "ComplaintTimeline", id: draftId }
      ]
    }),
    saveComplaintDraft: builder.mutation<
      ComplaintResponse,
      { draftId: string; body: SaveComplaintRequest }
    >({
      query: ({ draftId, body }) => ({
        url: `/complaint-drafts/${draftId}/save`,
        method: "POST",
        body
      }),
      invalidatesTags: (_result, _error, { draftId }) => [
        { type: "ComplaintDraft", id: draftId },
        { type: "ComplaintDraft", id: `${draftId}-status` },
        { type: "ComplaintTimeline", id: draftId },
        { type: "ComplaintLedger", id: "LIST" }
      ]
    }),
    getComplaintDraftStatus: builder.query<ComplaintDraftStatusResponse, string>({
      query: (draftId) => `/complaint-drafts/${draftId}/status`,
      providesTags: (_result, _error, draftId) => [{ type: "ComplaintDraft", id: `${draftId}-status` }]
    }),
    getComplaintMessages: builder.query<ComplaintMessageListResponse, string>({
      query: (draftId) => `/complaint-drafts/${draftId}/messages`,
      providesTags: (_result, _error, draftId) => [{ type: "ComplaintMessage", id: draftId }]
    }),
    uploadComplaintAttachment: builder.mutation<
      ComplaintAttachmentUploadResponse,
      { draftId: string; file: File }
    >({
      query: ({ draftId, file }) => {
        const body = new FormData();
        body.append("file", file);
        return {
          url: `/complaint-drafts/${draftId}/attachments`,
          method: "POST",
          body
        };
      },
      invalidatesTags: (_result, _error, { draftId }) => [
        { type: "ComplaintMessage", id: draftId },
        { type: "ComplaintEvidence", id: draftId },
        { type: "ComplaintTimeline", id: draftId }
      ]
    }),
    getComplaintAttachmentStatus: builder.query<
      ComplaintAttachmentStatusResponse,
      { draftId: string; attachmentId: string }
    >({
      query: ({ draftId, attachmentId }) =>
        `/complaint-drafts/${draftId}/attachments/${attachmentId}/status`,
      providesTags: (_result, _error, { attachmentId }) => [
        { type: "ComplaintAttachment", id: attachmentId }
      ]
    }),
    getComplaintEvidence: builder.query<FieldEvidenceListResponse, string>({
      query: (draftId) => `/complaint-drafts/${draftId}/evidence?active_only=true&limit=200`,
      providesTags: (_result, _error, draftId) => [{ type: "ComplaintEvidence", id: draftId }]
    }),
    getComplaintFieldEvidence: builder.query<
      FieldEvidenceDetailResponse,
      { draftId: string; fieldName: string }
    >({
      query: ({ draftId, fieldName }) => `/complaint-drafts/${draftId}/evidence/${fieldName}`,
      providesTags: (_result, _error, { draftId, fieldName }) => [
        { type: "ComplaintEvidence", id: `${draftId}-${fieldName}` }
      ]
    }),
    getComplaintTimeline: builder.query<TimelineListResponse, string>({
      query: (draftId) => `/complaint-drafts/${draftId}/timeline?limit=200`,
      providesTags: (_result, _error, draftId) => [{ type: "ComplaintTimeline", id: draftId }]
    }),
    sendComplaintMessage: builder.mutation<
      SendComplaintMessageResponse,
      { draftId: string; body: SendComplaintMessageRequest }
    >({
      query: ({ draftId, body }) => ({
        url: `/complaint-drafts/${draftId}/messages`,
        method: "POST",
        body
      }),
      invalidatesTags: (_result, _error, { draftId }) => [
        { type: "ComplaintMessage", id: draftId },
        { type: "ComplaintDraft", id: draftId },
        { type: "ComplaintEvidence", id: draftId },
        { type: "ComplaintTimeline", id: draftId }
      ]
    }),
    developmentPatchComplaintDraft: builder.mutation<
      ComplaintDraftResponse,
      { draftId: string; body: DevelopmentPatchRequest }
    >({
      query: ({ draftId, body }) => ({
        url: `/complaint-drafts/${draftId}/development-patch`,
        method: "PATCH",
        body
      }),
      invalidatesTags: (_result, _error, { draftId }) => [
        { type: "ComplaintDraft", id: draftId },
        { type: "ComplaintDraft", id: "ACTIVE" },
        { type: "ComplaintEvidence", id: draftId },
        { type: "ComplaintTimeline", id: draftId }
      ]
    }),
    getComplaints: builder.query<ComplaintLedgerListResponse, string | void>({
      query: (queryString) => `/complaints${queryString ? `?${queryString}` : ""}`,
      providesTags: () => [{ type: "ComplaintLedger", id: "LIST" }]
    }),
    getComplaint: builder.query<ComplaintResponse, string>({
      query: (complaintId) => `/complaints/${complaintId}`,
      providesTags: (_result, _error, complaintId) => [{ type: "ComplaintLedger", id: complaintId }]
    }),
    getComplaintVersions: builder.query<unknown[], string>({
      query: (complaintId) => `/complaints/${complaintId}/versions`,
      providesTags: (_result, _error, complaintId) => [
        { type: "ComplaintLedger", id: `${complaintId}-versions` }
      ]
    }),
    getComplaintLedgerTimeline: builder.query<TimelineListResponse, string>({
      query: (complaintId) => `/complaints/${complaintId}/timeline`,
      providesTags: (_result, _error, complaintId) => [
        { type: "ComplaintLedger", id: `${complaintId}-timeline` }
      ]
    }),
    getInspectionBrief: builder.query<InspectionBrief, string>({
      query: (complaintId) => `/complaints/${complaintId}/inspection-brief?format=json`,
      providesTags: (_result, _error, complaintId) => [
        { type: "InspectionBrief", id: complaintId }
      ]
    }),
    runBatchImpact: builder.mutation<BatchImpactResponse, { draftId: string; createdBy?: string }>({
      query: ({ draftId, createdBy }) => ({
        url: `/complaint-drafts/${draftId}/batch-impact`,
        method: "POST",
        body: { created_by: createdBy ?? "Demo User" }
      }),
      invalidatesTags: (_result, _error, { draftId }) => [{ type: "BatchImpact", id: draftId }]
    }),
    simulateBatchImpact: builder.mutation<
      ContainmentSimulationResponse,
      { draftId: string; body: ContainmentSimulationRequest }
    >({
      query: ({ draftId, body }) => ({
        url: `/complaint-drafts/${draftId}/batch-impact/simulate`,
        method: "POST",
        body
      })
    }),
    startQualityWarRoomRun: builder.mutation<
      QualityWarRoomRunStartedResponse,
      { draftId: string; createdBy?: string }
    >({
      query: ({ draftId, createdBy }) => ({
        url: `/complaint-drafts/${draftId}/quality-war-room/runs`,
        method: "POST",
        body: { created_by: createdBy ?? "Demo User" }
      }),
      invalidatesTags: (_result, _error, { draftId }) => [{ type: "QualityWarRoom", id: draftId }]
    }),
    getQualityWarRoomRuns: builder.query<QualityWarRoomRunResponse[], string>({
      query: (draftId) => `/complaint-drafts/${draftId}/quality-war-room/runs`,
      providesTags: (_result, _error, draftId) => [{ type: "QualityWarRoom", id: draftId }]
    }),
    getQualityWarRoomRun: builder.query<
      QualityWarRoomRunResponse,
      { draftId: string; runId: string }
    >({
      query: ({ draftId, runId }) => `/complaint-drafts/${draftId}/quality-war-room/runs/${runId}`,
      providesTags: (_result, _error, { draftId, runId }) => [
        { type: "QualityWarRoom", id: `${draftId}-${runId}` }
      ]
    }),
    runDuplicateAnalysis: builder.mutation<DuplicateAnalysisResult, { draftId: string; createdBy?: string }>({
      query: ({ draftId, createdBy }) => ({
        url: `/complaint-drafts/${draftId}/duplicate-analysis`,
        method: "POST",
        body: { created_by: createdBy ?? "Demo User" }
      }),
      invalidatesTags: (_result, _error, { draftId }) => [{ type: "InvestigationSupport", id: draftId }]
    }),
    runInvestigationPlaybook: builder.mutation<
      InvestigationPlaybookResult,
      { draftId: string; createdBy?: string }
    >({
      query: ({ draftId, createdBy }) => ({
        url: `/complaint-drafts/${draftId}/investigation-playbook`,
        method: "POST",
        body: { created_by: createdBy ?? "Demo User" }
      }),
      invalidatesTags: (_result, _error, { draftId }) => [{ type: "InvestigationSupport", id: draftId }]
    })
  })
});

export const {
  useCreateComplaintDraftMutation,
  useGetComplaintDraftQuery,
  useGetComplaintDraftStatusQuery,
  useGetComplaintAttachmentStatusQuery,
  useGetComplaintEvidenceQuery,
  useGetComplaintFieldEvidenceQuery,
  useGetComplaintTimelineQuery,
  useGetComplaintsQuery,
  useGetComplaintQuery,
  useGetComplaintVersionsQuery,
  useGetComplaintLedgerTimelineQuery,
  useGetInspectionBriefQuery,
  useRunBatchImpactMutation,
  useSimulateBatchImpactMutation,
  useStartQualityWarRoomRunMutation,
  useGetQualityWarRoomRunsQuery,
  useGetQualityWarRoomRunQuery,
  useRunDuplicateAnalysisMutation,
  useRunInvestigationPlaybookMutation,
  useGetComplaintMessagesQuery,
  useResetComplaintDraftMutation,
  useSaveComplaintDraftMutation,
  useSendComplaintMessageMutation,
  useUploadComplaintAttachmentMutation,
  useDevelopmentPatchComplaintDraftMutation
} = complaintApi;
