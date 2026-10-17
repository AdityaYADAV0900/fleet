import { useQuery } from '@tanstack/react-query';
import { sparesApi } from '../api/spares';

export const sparesKeys = {
  all: ['spares'] as const,
  inventory: (params?: Record<string, unknown>) => ['spares', 'inventory', params] as const,
  parts: ['spares', 'parts'] as const,
  transactions: (params?: Record<string, unknown>) => ['spares', 'transactions', params] as const,
};

export function useInventory(params?: {
  part_number?: string;
  location_id?: string;
  low_stock?: boolean;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: sparesKeys.inventory(params),
    queryFn: () => sparesApi.listInventory(params),
    staleTime: 60_000,
  });
}

export function useSpareParts() {
  return useQuery({
    queryKey: sparesKeys.parts,
    queryFn: sparesApi.listSpareParts,
    staleTime: 5 * 60_000,
  });
}

export function useInventoryTransactions(params?: {
  part_number?: string;
  type?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: sparesKeys.transactions(params),
    queryFn: () => sparesApi.listTransactions(params),
    staleTime: 60_000,
  });
}
