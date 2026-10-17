import { useQuery } from '@tanstack/react-query';
import { fleetApi } from '../api/fleet';

export const fleetKeys = {
  all: ['fleet'] as const,
  aircraftList: (params?: Record<string, unknown>) => ['fleet', 'aircraft', params] as const,
  aircraftDetail: (id: string) => ['fleet', 'aircraft-detail', id] as const,
  systems: ['fleet', 'systems'] as const,
  componentTypes: (systemId?: string) => ['fleet', 'component-types', systemId] as const,
  components: (params?: Record<string, unknown>) => ['fleet', 'components', params] as const,
};

export function useAircraftList(params?: { state?: string; base?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: fleetKeys.aircraftList(params),
    queryFn: () => fleetApi.listAircraft(params),
    staleTime: 60_000,
  });
}

export function useAircraftDetail(id?: string) {
  return useQuery({
    queryKey: id ? fleetKeys.aircraftDetail(id) : ['disabled'],
    queryFn: () => (id ? fleetApi.getAircraftDetail(id) : Promise.reject('No ID')),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useSystems() {
  return useQuery({
    queryKey: fleetKeys.systems,
    queryFn: fleetApi.listSystems,
    staleTime: 5 * 60_000,
  });
}

export function useComponentTypes(systemId?: string) {
  return useQuery({
    queryKey: fleetKeys.componentTypes(systemId),
    queryFn: () => fleetApi.listComponentTypes(systemId ? { system_id: systemId } : undefined),
    staleTime: 5 * 60_000,
  });
}

export function useComponents(params?: { aircraft_id?: string; status?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: fleetKeys.components(params),
    queryFn: () => fleetApi.listComponents(params),
    staleTime: 60_000,
  });
}
