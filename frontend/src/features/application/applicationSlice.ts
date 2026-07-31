import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { fetchAiStatus, fetchHealth } from "../../services/apiClient";
import type {
  AiStatusResponse,
  BackendConnectionState,
  DatabaseConnectionState,
  HealthResponse
} from "../../types/health";

export interface ApplicationStatusState {
  frontendStatus: "ready";
  backendStatus: BackendConnectionState;
  databaseStatus: DatabaseConnectionState;
  health: HealthResponse | null;
  aiStatus: AiStatusResponse | null;
  demoAiMode: "live" | "deterministic";
  errorMessage: string | null;
}

const initialState: ApplicationStatusState = {
  frontendStatus: "ready",
  backendStatus: "checking",
  databaseStatus: "checking",
  health: null,
  aiStatus: null,
  demoAiMode: "live",
  errorMessage: null
};

export const checkBackendHealth = createAsyncThunk(
  "applicationStatus/checkBackendHealth",
  async () => {
    const health = await fetchHealth();
    const aiStatus = await fetchAiStatus().catch(() => null);
    return { health, aiStatus };
  }
);

export const applicationStatusSlice = createSlice({
  name: "applicationStatus",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(checkBackendHealth.pending, (state) => {
        state.backendStatus = "checking";
        state.databaseStatus = "checking";
        state.errorMessage = null;
      })
      .addCase(checkBackendHealth.fulfilled, (state, action) => {
        state.health = action.payload.health;
        state.aiStatus = action.payload.aiStatus;
        state.demoAiMode = action.payload.aiStatus?.demo_ai_mode ?? "live";
        state.backendStatus = "connected";
        state.databaseStatus = action.payload.health.database.status;
      })
      .addCase(checkBackendHealth.rejected, (state) => {
        state.health = null;
        state.aiStatus = null;
        state.demoAiMode = "live";
        state.backendStatus = "unavailable";
        state.databaseStatus = "unavailable";
        state.errorMessage = "Backend API unavailable";
      });
  }
});
