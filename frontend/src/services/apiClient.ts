import type { AiStatusResponse, HealthResponse } from "../types/health";

const defaultApiBaseUrl = "http://127.0.0.1:8000/api/v1";

export function getApiBaseUrl() {
  return (import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl).replace(/\/$/, "");
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${getApiBaseUrl()}/health`, {
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error("Backend health check failed");
  }

  const payload = await response.json() as HealthResponse;
  if (payload.service !== "pharmaq-sentinel-api" || !payload.database?.status) {
    throw new Error("Backend health response was malformed");
  }

  return payload;
}

export async function fetchAiStatus(): Promise<AiStatusResponse> {
  const response = await fetch(`${getApiBaseUrl()}/ai/status`, {
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error("AI status check failed");
  }

  const payload = await response.json() as AiStatusResponse;
  if (payload.provider !== "openai" || !payload.demo_ai_mode) {
    throw new Error("AI status response was malformed");
  }

  return payload;
}
