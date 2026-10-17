import { api } from './client';
import type {
  AvailabilityTrendOut,
  FleetSummaryOut,
  KpiResponse,
  ScenarioRunOut,
} from '../types/api';

export const availabilityApi = {
  getKpis: (params?: { as_of?: string }) =>
    api.get<KpiResponse>('/kpis', params),

  getFleetSummary: (params?: { as_of?: string }) =>
    api.get<FleetSummaryOut>('/fleet/summary', params),

  getAvailabilityTrend: (params?: { days?: number; as_of?: string }) =>
    api.get<AvailabilityTrendOut>('/fleet/availability/trend', params),

  runScenario: (payload: {
    type: string;
    params?: Record<string, unknown>;
    horizon_days?: number;
    runs?: number;
    seed?: number;
  }) => api.post<ScenarioRunOut>('/scenarios/run', payload),

  listScenarios: (limit: number = 20) =>
    api.get<Array<{ id: string; type: string; created_at: string; seed: number; created_by?: string; results: unknown }>>(
      '/scenarios',
      { limit }
    ),
};
