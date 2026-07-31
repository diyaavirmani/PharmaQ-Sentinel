export type BackendConnectionState = "checking" | "connected" | "unavailable";
export type DatabaseConnectionState = "checking" | "connected" | "unavailable";

export interface DatabaseHealth {
  provider: "mysql";
  status: "connected" | "unavailable";
}

export interface HealthResponse {
  status: "healthy" | "degraded";
  service: "pharmaq-sentinel-api";
  version: string;
  database: DatabaseHealth;
}

export interface AiStatusResponse {
  provider: "openai";
  configured: boolean;
  available: boolean;
  model_configured: boolean;
  model: string | null;
  demo_ai_mode: "live" | "deterministic";
  last_checked_at: string;
  message: string;
}
