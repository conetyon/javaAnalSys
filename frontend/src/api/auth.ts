/**
 * Authentication API
 */

import axios from 'axios';
import type { ApiResponse } from '../types/api';
import type { LoginRequest, RegisterRequest, TokenResponse, UserInfo } from '../types/auth';

// Use raw axios for auth endpoints to avoid interceptor loops
const authClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Register a new user
 */
export async function register(data: RegisterRequest): Promise<UserInfo> {
  const response = await authClient.post<ApiResponse<UserInfo>>('/auth/register', data);
  if (response.data.code !== 201) {
    throw new Error(response.data.message || 'Registration failed');
  }
  return response.data.data!;
}

/**
 * Login and get tokens
 */
export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await authClient.post<ApiResponse<TokenResponse>>('/auth/login', data);
  if (response.data.code !== 200) {
    throw new Error(response.data.message || 'Login failed');
  }
  return response.data.data!;
}

/**
 * Refresh access token
 */
export async function refreshToken(refresh_token: string): Promise<TokenResponse> {
  const response = await authClient.post<ApiResponse<TokenResponse>>('/auth/refresh', {
    refresh_token,
  });
  if (response.data.code !== 200) {
    throw new Error(response.data.message || 'Token refresh failed');
  }
  return response.data.data!;
}
