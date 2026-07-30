import { combineReducers, configureStore } from "@reduxjs/toolkit";
import {
  applicationStatusSlice,
  checkBackendHealth
} from "../features/application/applicationSlice";
import { complaintApi } from "../features/complaint/complaintApi";
import { complaintSlice } from "../features/complaint/complaintSlice";

const rootReducer = combineReducers({
  applicationStatus: applicationStatusSlice.reducer,
  complaint: complaintSlice.reducer,
  [complaintApi.reducerPath]: complaintApi.reducer
});

export type RootState = ReturnType<typeof rootReducer>;

export function createAppStore(preloadedState?: Partial<RootState>) {
  return configureStore({
    reducer: rootReducer,
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(complaintApi.middleware),
    preloadedState
  });
}

export const store = createAppStore();

export type AppStore = ReturnType<typeof createAppStore>;
export type AppDispatch = AppStore["dispatch"];

export { checkBackendHealth };
