import { api } from './client';
import type {
  AircraftDetailOut,
  AircraftListOut,
  ComponentOut,
  ComponentTypeOut,
  PaginatedResponse,
  SystemOut,
} from '../types/api';

export const fleetApi = {
  listAircraft: (params?: { state?: string; base?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<AircraftListOut>>('/aircraft', params),

  getAircraftDetail: (id: string) =>
    api.get<AircraftDetailOut>(`/aircraft/${id}`),

  listSystems: () =>
    api.get<SystemOut[]>('/systems'),

  listComponentTypes: (params?: { system_id?: string }) =>
    api.get<ComponentTypeOut[]>('/component-types', params),

  listComponents: (params?: { aircraft_id?: string; status?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<ComponentOut>>('/components', params),
};
