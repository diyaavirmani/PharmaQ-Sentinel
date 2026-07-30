import { createApi, type BaseQueryFn } from "@reduxjs/toolkit/query/react";
import { getApiBaseUrl } from "../../services/apiClient";
import type {
  ComplaintDraftResponse,
  ComplaintDraftStatusResponse,
  CreateComplaintDraftRequest,
  DevelopmentPatchRequest
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
    headers.set("Content-Type", "application/json");
    init.body = JSON.stringify(request.body);
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
  tagTypes: ["ComplaintDraft"],
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
        { type: "ComplaintDraft", id: "ACTIVE" }
      ]
    }),
    getComplaintDraftStatus: builder.query<ComplaintDraftStatusResponse, string>({
      query: (draftId) => `/complaint-drafts/${draftId}/status`,
      providesTags: (_result, _error, draftId) => [{ type: "ComplaintDraft", id: `${draftId}-status` }]
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
        { type: "ComplaintDraft", id: "ACTIVE" }
      ]
    })
  })
});

export const {
  useCreateComplaintDraftMutation,
  useGetComplaintDraftQuery,
  useGetComplaintDraftStatusQuery,
  useResetComplaintDraftMutation,
  useDevelopmentPatchComplaintDraftMutation
} = complaintApi;
