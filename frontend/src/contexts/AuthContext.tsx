/**
 * Authentication Context
 *
 * Provides authentication state and methods to the entire app.
 * Handles token storage, login, logout, and auto-refresh.
 */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { message } from 'antd';
import { login as apiLogin, register as apiRegister, refreshToken } from '../api/auth';
import type { LoginRequest, RegisterRequest, UserInfo, TokenResponse } from '../types/auth';

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_INFO_KEY = 'user_info';

interface AuthContextType {
  isAuthenticated: boolean;
  user: UserInfo | null;
  loading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  getAccessToken: () => string | null;
}

const AuthContext = createContext<AuthContextType | null>(null);

/**
 * Parse JWT payload without verification (for extracting user info)
 */
function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(payload);
  } catch {
    return null;
  }
}

/**
 * Check if token is expired
 */
function isTokenExpired(token: string): boolean {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') return true;
  // Add 10 second buffer
  return payload.exp * 1000 < Date.now() + 10000;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedUser = localStorage.getItem(USER_INFO_KEY);
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);

    if (storedUser && accessToken && !isTokenExpired(accessToken)) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        clearTokens();
      }
    } else if (accessToken && isTokenExpired(accessToken)) {
      // Try to refresh token
      const refreshTokenValue = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (refreshTokenValue && !isTokenExpired(refreshTokenValue)) {
        refreshToken(refreshTokenValue)
          .then((tokens) => {
            saveTokens(tokens);
            const storedUserRetry = localStorage.getItem(USER_INFO_KEY);
            if (storedUserRetry) {
              setUser(JSON.parse(storedUserRetry));
            }
          })
          .catch(() => {
            clearTokens();
          });
      } else {
        clearTokens();
      }
    }

    setLoading(false);
  }, []);

  const saveTokens = useCallback((tokens: TokenResponse, userInfo?: UserInfo) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    if (userInfo) {
      localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));
    }
  }, []);

  const clearTokens = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_INFO_KEY);
    setUser(null);
  }, []);

  const login = useCallback(async (data: LoginRequest) => {
    const response = await apiLogin(data);
    // Use user info from response (backend returns it in login response)
    const userInfo: UserInfo = response.user || {
      id: parseJwtPayload(response.access_token)?.user_id as number,
      username: data.username,
      role: 'user',
    };
    saveTokens(response, userInfo);
    setUser(userInfo);
    message.success('Login successful');
  }, [saveTokens]);

  const register = useCallback(async (data: RegisterRequest) => {
    const userInfo = await apiRegister(data);
    // Auto login after registration
    const tokens = await apiLogin({ username: data.username, password: data.password });
    saveTokens(tokens, userInfo);
    setUser(userInfo);
    message.success('Registration successful');
  }, [saveTokens]);

  const logout = useCallback(() => {
    clearTokens();
    message.info('Logged out');
  }, [clearTokens]);

  const getAccessToken = useCallback(() => {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!user,
        user,
        loading,
        login,
        register,
        logout,
        getAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to access auth context
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
