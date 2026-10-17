import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { engineApi } from '../api/engine';
import { availabilityKeys } from './useAvailabilityQueries';

export const engineKeys = {
  all: ['engine'] as const,
  predictions: (params?: Record<string, unknown>) => [...engineKeys.all, 'predictions', params] as const,
  advisories: (params?: Record<string, unknown>) => [...engineKeys.all, 'advisories', params] as const,
  advisory: (id: string) => [...engineKeys.all, 'advisory', id] as const,
  alerts: (params?: Record<string, unknown>) => [...engineKeys.all, 'alerts', params] as const,
};

export function usePredictions(params?: {
  aircraft_id?: string;
  system?: string;
  min_risk?: number;
  as_of_date?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: engineKeys.predictions(params),
    queryFn: () => engineApi.listPredictions(params),
    staleTime: 60_000,
  });
}

export function useAdvisories(params?: {
  priority?: string;
  status?: string;
  spare_status?: string;
  aircraft_id?: string;
  as_of_date?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: engineKeys.advisories(params),
    queryFn: () => engineApi.listAdvisories(params),
    staleTime: 30_000,
  });
}

export function useAdvisory(id?: string) {
  return useQuery({
    queryKey: id ? engineKeys.advisory(id) : ['disabled'],
    queryFn: () => (id ? engineApi.getAdvisory(id) : Promise.reject('No ID')),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useUpdateAdvisory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { status: string; reason?: string } }) =>
      engineApi.updateAdvisory(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engineKeys.advisories() });
      queryClient.invalidateQueries({ queryKey: availabilityKeys.all });
    },
  });
}

export function useAlerts(params?: {
  severity?: string;
  acknowledged?: boolean;
  type?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: engineKeys.alerts(params),
    queryFn: () => engineApi.listAlerts(params),
    staleTime: 30_000,
  });
}

export function useAckAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ack }: { id: number; ack?: boolean }) => engineApi.acknowledgeAlert(id, ack ?? true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engineKeys.alerts() });
    },
  });
}

export function useRunEngine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: engineApi.runEngine,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engineKeys.all });
      queryClient.invalidateQueries({ queryKey: availabilityKeys.all });
    },
  });
}
