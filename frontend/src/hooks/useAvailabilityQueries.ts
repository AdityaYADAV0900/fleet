import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { availabilityApi } from '../api/availability';

export const availabilityKeys = {
  all: ['availability'] as const,
  kpis: (asOf?: string | null) => [...availabilityKeys.all, 'kpis', asOf] as const,
  summary: (asOf?: string | null) => [...availabilityKeys.all, 'summary', asOf] as const,
  trend: (days?: number, asOf?: string | null) => [...availabilityKeys.all, 'trend', days, asOf] as const,
  scenarios: ['scenarios'] as const,
};

export function useKpis(asOf?: string | null) {
  return useQuery({
    queryKey: availabilityKeys.kpis(asOf),
    queryFn: () => availabilityApi.getKpis(asOf ? { as_of: asOf } : undefined),
    staleTime: 60_000,
  });
}

export function useFleetSummary(asOf?: string | null) {
  return useQuery({
    queryKey: availabilityKeys.summary(asOf),
    queryFn: () => availabilityApi.getFleetSummary(asOf ? { as_of: asOf } : undefined),
    staleTime: 60_000,
  });
}

export function useAvailabilityTrend(days: number = 30, asOf?: string | null) {
  return useQuery({
    queryKey: availabilityKeys.trend(days, asOf),
    queryFn: () => availabilityApi.getAvailabilityTrend({ days, as_of: asOf || undefined }),
    staleTime: 60_000,
  });
}

export function useScenarioHistory() {
  return useQuery({
    queryKey: availabilityKeys.scenarios,
    queryFn: () => availabilityApi.listScenarios(20),
    staleTime: 30_000,
  });
}

export function useRunScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: availabilityApi.runScenario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: availabilityKeys.scenarios });
    },
  });
}
