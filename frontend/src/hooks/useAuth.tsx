import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { authApi } from '../api/auth';
import { getStoredToken, setStoredToken, ApiError } from '../api/client';
import type { UserOut, UserRole } from '../types/api';

export const MOCK_USERS: Record<UserRole, UserOut> = {
  commander: {
    id: 1,
    username: 'commander',
    role: 'commander',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
  },
  planner: {
    id: 2,
    username: 'planner',
    role: 'planner',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
  },
  technician: {
    id: 3,
    username: 'technician',
    role: 'technician',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
  },
};

const DEMO_CREDENTIALS: Record<UserRole, { user: string; pass: string }> = {
  commander: { user: 'commander', pass: 'commander123' },
  planner: { user: 'planner', pass: 'planner123' },
  technician: { user: 'technician', pass: 'technician123' },
};

function getStoredMockUser(): UserOut | null {
  try {
    const raw = localStorage.getItem('fleet_auth_mock_user');
    if (!raw) return null;
    return JSON.parse(raw) as UserOut;
  } catch {
    return null;
  }
}

function isMockSessionActive(): boolean {
  return localStorage.getItem('fleet_auth_is_mock') === 'true';
}

interface AuthContextType {
  user: UserOut | null;
  role: UserRole | null;
  token: string | null;
  isLoading: boolean;
  isMockMode: boolean;
  asOfDate: string | null;
  setAsOfDate: (date: string | null) => void;
  login: (username: string, password: string) => Promise<void>;
  mockLogin: (role?: UserRole, customUsername?: string) => void;
  switchDemoRole: (role: UserRole) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setTokenState] = useState<string | null>(getStoredToken());
  const [user, setUser] = useState<UserOut | null>(() => getStoredMockUser());
  const [isMockMode, setIsMockMode] = useState<boolean>(() => isMockSessionActive());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [asOfDate, setAsOfDate] = useState<string | null>('2025-11-25');

  const mockLogin = useCallback((role: UserRole = 'commander', customUsername?: string) => {
    const template = MOCK_USERS[role] || MOCK_USERS.commander;
    const mockUser: UserOut = {
      ...template,
      username: customUsername?.trim() || template.username,
      role,
    };
    const mockToken = `mock-token-${role}-${Date.now()}`;
    setStoredToken(mockToken);
    localStorage.setItem('fleet_auth_mock_user', JSON.stringify(mockUser));
    localStorage.setItem('fleet_auth_is_mock', 'true');
    setTokenState(mockToken);
    setUser(mockUser);
    setIsMockMode(true);
    setIsLoading(false);
  }, []);

  const fetchCurrentUser = useCallback(async () => {
    const currentToken = getStoredToken();
    const mockFlag = isMockSessionActive();
    const storedMock = getStoredMockUser();

    if (!currentToken) {
      setUser(null);
      setIsMockMode(false);
      setIsLoading(false);
      return;
    }

    // If session is marked as mock or token is mock, restore session without hitting backend
    if ((mockFlag && storedMock) || currentToken.startsWith('mock-token-')) {
      const roleGuess: UserRole = currentToken.includes('technician')
        ? 'technician'
        : currentToken.includes('planner')
        ? 'planner'
        : 'commander';
      const userToRestore = storedMock || MOCK_USERS[roleGuess];
      setUser(userToRestore);
      setIsMockMode(true);
      setIsLoading(false);
      return;
    }

    try {
      const userData = await authApi.getMe();
      setUser(userData);
      setIsMockMode(false);
    } catch (err: unknown) {
      console.warn('Backend /auth/me check failed:', err);
      // If we already had a stored mock user, keep mock session active
      if (storedMock) {
        setUser(storedMock);
        setIsMockMode(true);
      } else {
        // If token expired or invalid and not mock, reset
        setStoredToken(null);
        setTokenState(null);
        setUser(null);
        setIsMockMode(false);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const login = useCallback(
    async (username: string, password: string) => {
      setIsLoading(true);
      try {
        const res = await authApi.login(username, password);
        setStoredToken(res.access_token);
        setTokenState(res.access_token);
        localStorage.removeItem('fleet_auth_mock_user');
        localStorage.removeItem('fleet_auth_is_mock');
        setIsMockMode(false);
        await fetchCurrentUser();
      } catch (err: unknown) {
        // If active backend rejected with 400 or 401, rethrow
        if (err instanceof ApiError && (err.status === 400 || err.status === 401)) {
          throw err;
        }

        // Backend unreachable, offline, network error, or 502/503:
        console.warn('Backend unavailable, activating mock login fallback:', err);
        const normalized = username.trim().toLowerCase();
        let targetRole: UserRole = 'commander';
        if (normalized.includes('technician') || normalized.includes('tech')) {
          targetRole = 'technician';
        } else if (normalized.includes('planner') || normalized.includes('plan')) {
          targetRole = 'planner';
        }
        mockLogin(targetRole, username);
      } finally {
        setIsLoading(false);
      }
    },
    [fetchCurrentUser, mockLogin]
  );

  const switchDemoRole = useCallback(
    async (role: UserRole) => {
      if (isMockMode) {
        mockLogin(role);
        return;
      }
      const creds = DEMO_CREDENTIALS[role];
      if (creds) {
        try {
          await login(creds.user, creds.pass);
        } catch {
          // If backend unavailable or login threw, activate mockLogin
          mockLogin(role);
        }
      } else {
        mockLogin(role);
      }
    },
    [isMockMode, login, mockLogin]
  );

  const logout = useCallback(() => {
    setStoredToken(null);
    setTokenState(null);
    setUser(null);
    setIsMockMode(false);
    localStorage.removeItem('fleet_auth_mock_user');
    localStorage.removeItem('fleet_auth_is_mock');
  }, []);

  const value = useMemo<AuthContextType>(
    () => ({
      user,
      role: user?.role || null,
      token,
      isLoading,
      isMockMode,
      asOfDate,
      setAsOfDate,
      login,
      mockLogin,
      switchDemoRole,
      logout,
    }),
    [user, token, isLoading, isMockMode, asOfDate, login, mockLogin, switchDemoRole, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
