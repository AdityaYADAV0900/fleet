import { api } from './client';
import type {
  InventoryOut,
  InventoryTransactionOut,
  PaginatedResponse,
  SparePartOut,
} from '../types/api';

export const sparesApi = {
  listInventory: (params?: {
    part_number?: string;
    location_id?: string;
    low_stock?: boolean;
    page?: number;
    page_size?: number;
  }) => api.get<PaginatedResponse<InventoryOut>>('/inventory', params),

  listSpareParts: () =>
    api.get<SparePartOut[]>('/inventory/parts'),

  listTransactions: (params?: {
    part_number?: string;
    type?: string;
    page?: number;
    page_size?: number;
  }) => api.get<PaginatedResponse<InventoryTransactionOut>>('/inventory/transactions', params),
};
