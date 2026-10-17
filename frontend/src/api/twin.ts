import { api } from './client';
import type {
  ScenarioRunOut,
  TwinAircraftNodeOut,
  TwinComponentDetailOut,
  TwinFleetOut,
} from '../types/api';

export const twinApi = {
  getFleetTwin: (params?: { as_of?: string }) =>
    api.get<TwinFleetOut>('/twin/fleet', params),

  getAircraftTwin: (id: string, params?: { as_of?: string }) =>
    api.get<TwinAircraftNodeOut>(`/twin/aircraft/${id}`, params),

  getComponentTwin: (id: string, params?: { as_of?: string }) =>
    api.get<TwinComponentDetailOut>(`/twin/component/${id}`, params),

  runWhatIf: (payload: {
    type: string;
    params?: Record<string, unknown>;
    horizon_days?: number;
    runs?: number;
    seed?: number;
  }) => api.post<ScenarioRunOut>('/twin/whatif', payload),
};
