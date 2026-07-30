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
