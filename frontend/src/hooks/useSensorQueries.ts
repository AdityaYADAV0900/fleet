import { useQuery } from '@tanstack/react-query';
import { sensorsApi } from '../api/sensors';

export const sensorKeys = {
  all: ['sensors'] as const,
  readings: (componentId: string, params?: Record<string, unknown>) =>
    [...sensorKeys.all, 'readings', componentId, params] as const,
  anomalies: (componentId: string, params?: Record<string, unknown>) =>
    [...sensorKeys.all, 'anomalies', componentId, params] as const,
  faults: (params?: Record<string, unknown>) => [...sensorKeys.all, 'faults', params] as const,
};

export function useComponentAnomalies(componentId?: string, params?: { limit?: number }) {
  return useQuery({
    queryKey: componentId ? sensorKeys.anomalies(componentId, params) : ['disabled'],
    queryFn: () => (componentId ? sensorsApi.getComponentAnomalies(componentId, params) : Promise.reject('No ID')),
    enabled: !!componentId,
    staleTime: 60_000,
  });
}

export function useComponentSensors(
  componentId?: string,
  params?: { parameter?: string; from_date?: string; to_date?: string; limit?: number }
) {
  return useQuery({
    queryKey: componentId ? sensorKeys.readings(componentId, params) : ['disabled'],
    queryFn: () => (componentId ? sensorsApi.getComponentSensors(componentId, params) : Promise.reject('No ID')),
    enabled: !!componentId,
    staleTime: 60_000,
  });
}

export function useFaultEvents(params?: {
  aircraft_id?: string;
  component_id?: string;
  severity?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: sensorKeys.faults(params),
    queryFn: () => sensorsApi.listFaultEvents(params),
    staleTime: 60_000,
  });
}
