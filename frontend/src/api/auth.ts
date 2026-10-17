import { api } from './client';
import type { TokenResponse, UserOut } from '../types/api';

export const authApi = {
  login: (username: string, password: string): Promise<TokenResponse> =>
    api.post<TokenResponse>('/auth/login', { username, password }),

  getMe: (): Promise<UserOut> =>
    api.get<UserOut>('/auth/me'),
};
