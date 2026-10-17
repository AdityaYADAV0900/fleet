import { useQuery, useMutation } from '@tanstack/react-query';
import { twinApi } from '../api/twin';

export const twinKeys = {
  all: ['twin'] as const,
  fleet: (asOf?: string | null) => [...twinKeys.all, 'fleet', asOf] as const,
  aircraft: (id: string, asOf?: string | null) => [...twinKeys.all, 'aircraft', id, asOf] as const,
  component: (id: string, asOf?: string | null) => [...twinKeys.all, 'component', id, asOf] as const,
};

export function useFleetTwin(asOf?: string | null) {
  return useQuery({
    queryKey: twinKeys.fleet(asOf),
    queryFn: () => twinApi.getFleetTwin(asOf ? { as_of: asOf } : undefined),
    staleTime: 60_000,
  });
}

export function useAircraftTwin(id?: string, asOf?: string | null) {
  return useQuery({
    queryKey: id ? twinKeys.aircraft(id, asOf) : ['disabled'],
    queryFn: () => (id ? twinApi.getAircraftTwin(id, asOf ? { as_of: asOf } : undefined) : Promise.reject('No ID')),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useComponentTwin(id?: string, asOf?: string | null) {
  return useQuery({
    queryKey: id ? twinKeys.component(id, asOf) : ['disabled'],
    queryFn: () => (id ? twinApi.getComponentTwin(id, asOf ? { as_of: asOf } : undefined) : Promise.reject('No ID')),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useTwinWhatIf() {
  return useMutation({
    mutationFn: twinApi.runWhatIf,
  });
}
