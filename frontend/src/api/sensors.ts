import { api } from './client';
import type { AnomalyScoreOut, FaultEventOut, SensorReadingOut } from '../types/api';

export const sensorsApi = {
  getComponentSensors: (
    componentId: string,
    params?: {
      parameter?: string;
      from_date?: string;
      to_date?: string;
      limit?: number;
    }
  ) => api.get<SensorReadingOut[]>(`/components/${componentId}/sensors`, params),

  getComponentAnomalies: (componentId: string, params?: { limit?: number }) =>
    api.get<AnomalyScoreOut[]>(`/components/${componentId}/anomalies`, params),

  listFaultEvents: (params?: {
    aircraft_id?: string;
    component_id?: string;
    severity?: string;
    limit?: number;
  }) => api.get<FaultEventOut[]>('/fault-events', params),
};
