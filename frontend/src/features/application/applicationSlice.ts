import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { fetchHealth } from "../../services/apiClient";
import type { BackendConnectionState, DatabaseConnectionState, HealthResponse } from "../../types/health";

export interface ApplicationStatusState {
  frontendStatus: "ready";
  backendStatus: BackendConnectionState;
  databaseStatus: DatabaseConnectionState;
  health: HealthResponse | null;
  errorMessage: string | null;
}

const initialState: ApplicationStatusState = {
  frontendStatus: "ready",
  backendStatus: "checking",
  databaseStatus: "checking",
  health: null,
  errorMessage: null
};

export const checkBackendHealth = createAsyncThunk(
  "applicationStatus/checkBackendHealth",
  async () => fetchHealth()
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
        state.health = action.payload;
        state.backendStatus = "connected";
        state.databaseStatus = action.payload.database.status;
      })
      .addCase(checkBackendHealth.rejected, (state) => {
        state.health = null;
        state.backendStatus = "unavailable";
        state.databaseStatus = "unavailable";
        state.errorMessage = "Backend API unavailable";
      });
  }
});
