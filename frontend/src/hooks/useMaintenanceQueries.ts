import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { maintenanceApi } from '../api/maintenance';
import type { WorkOrderCreateIn } from '../types/api';

export const maintenanceKeys = {
  all: ['maintenance'] as const,
  workOrders: (params?: Record<string, unknown>) => ['maintenance', 'work-orders', params] as const,
  events: (params?: Record<string, unknown>) => ['maintenance', 'events', params] as const,
  agencies: ['maintenance', 'agencies'] as const,
  tasks: (aircraftId?: string) => ['maintenance', 'tasks', aircraftId] as const,
};

export function useCreateWorkOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WorkOrderCreateIn) => maintenanceApi.createWorkOrder(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: maintenanceKeys.all });
      queryClient.invalidateQueries({ queryKey: ['engine'] });
      queryClient.invalidateQueries({ queryKey: ['availability'] });
      queryClient.invalidateQueries({ queryKey: ['spares'] });
    },
  });
}

export function useWorkOrders(params?: {
  status?: string;
  agency?: string;
  aircraft?: string;
  priority?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: maintenanceKeys.workOrders(params),
    queryFn: () => maintenanceApi.listWorkOrders(params),
    staleTime: 60_000,
  });
}

export function useMaintenanceEvents(params?: {
  aircraft_id?: string;
  component_id?: string;
  type?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: maintenanceKeys.events(params),
    queryFn: () => maintenanceApi.listMaintenanceEvents(params),
    staleTime: 60_000,
  });
}

export function useAgencies() {
  return useQuery({
    queryKey: maintenanceKeys.agencies,
    queryFn: maintenanceApi.listAgencies,
    staleTime: 5 * 60_000,
  });
}

export function useScheduledTasks(aircraftId?: string) {
  return useQuery({
    queryKey: maintenanceKeys.tasks(aircraftId),
    queryFn: () => maintenanceApi.listScheduledTasks(aircraftId ? { aircraft_id: aircraftId } : undefined),
    staleTime: 60_000,
  });
}
