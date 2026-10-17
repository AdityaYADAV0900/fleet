import { api } from './client';
import type {
  AdvisoryOut,
  AlertOut,
  EngineRunSummaryOut,
  PaginatedResponse,
  PredictionOut,
} from '../types/api';

export const engineApi = {
  listPredictions: (params?: {
    aircraft_id?: string;
    system?: string;
    min_risk?: number;
    as_of_date?: string;
    page?: number;
    page_size?: number;
  }) => api.get<PaginatedResponse<PredictionOut>>('/predictions', params),

  listAdvisories: (params?: {
    priority?: string;
    status?: string;
    spare_status?: string;
    aircraft_id?: string;
    as_of_date?: string;
    page?: number;
    page_size?: number;
  }) => api.get<PaginatedResponse<AdvisoryOut>>('/advisories', params),

  getAdvisory: (id: string) =>
    api.get<AdvisoryOut>(`/advisories/${id}`),

  updateAdvisory: (id: string, payload: { status: string; reason?: string }) =>
    api.patch<AdvisoryOut>(`/advisories/${id}`, payload),

  listAlerts: (params?: {
    severity?: string;
    acknowledged?: boolean;
    type?: string;
    page?: number;
    page_size?: number;
  }) => api.get<PaginatedResponse<AlertOut>>('/alerts', params),

  acknowledgeAlert: (id: number, acknowledged: boolean = true) =>
    api.patch<AlertOut>(`/alerts/${id}/ack`, { acknowledged }),

  runEngine: (payload?: { as_of_date?: string; aircraft_id?: string }) =>
    api.post<EngineRunSummaryOut>('/engine/run', payload || {}),
};
