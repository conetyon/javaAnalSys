/**
 * Axios instance configuration
 * Handles request/response interceptors including:
 * - Automatic token injection
 * - Token refresh on 401
 * - Error handling
 */

import axios from 'axios';
import { Modal } from 'antd';
import type { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

// Internal type for API error response
interface ApiErrorResponse {
  code: number;
  message: string;
  error?: string;
}

// Token storage keys (must match AuthContext)
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Add Authorization header
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: Handle 401 and errors
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(callback: (token: string) => void) {
  refreshSubscribers.push(callback);
}

function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
}

function clearTokensAndRedirect() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem('user_info');
  window.location.href = '/login';
}

function handleSessionExpired() {
  Modal.warning({
    title: 'Session Expired',
    content: 'Your session has expired. Please log in again.',
    okText: 'Log In',
    onOk: clearTokensAndRedirect,
  });
}

client.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<ApiErrorResponse>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response?.status;
    const errorData = error.response?.data;

    // Handle 401 Unauthorized
    if (status === 401 && originalRequest && !originalRequest._retry) {
      // Check for single-device kickout
      const errorDetail = errorData?.error;
      if (errorDetail === 'Session expired, please login again') {
        Modal.warning({
          title: 'Logged Out',
          content: 'Your account has been logged in from another device.',
          okText: 'Log In Again',
          onOk: clearTokensAndRedirect,
        });
        return Promise.reject(error);
      }

      // Skip refresh for auth endpoints
      if (originalRequest.url?.includes('/auth/')) {
        return Promise.reject(error);
      }

      // Try to refresh token
      const refreshTokenValue = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (!refreshTokenValue) {
        handleSessionExpired();
        return Promise.reject(error);
      }

      if (!isRefreshing) {
        isRefreshing = true;

        try {
          // Use raw axios to avoid interceptor loop
          const response = await axios.post('/api/auth/refresh', {
            refresh_token: refreshTokenValue,
          });

          const newAccessToken = response.data.data.access_token;
          localStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken);

          isRefreshing = false;
          onTokenRefreshed(newAccessToken);

          // Retry original request
          originalRequest._retry = true;
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return client(originalRequest);

        } catch {
          isRefreshing = false;
          handleSessionExpired();
          return Promise.reject(error);
        }
      }

      // Queue request while refreshing
      return new Promise((resolve) => {
        subscribeTokenRefresh((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          resolve(client(originalRequest));
        });
      });
    }

    // Handle other errors
    // 400/404/422: Business errors, show to user
    if (status && [400, 404, 422].includes(status)) {
      const message = errorData?.message || errorData?.error || 'Request failed';
      return Promise.reject(new Error(message));
    }

    // 500+: Server errors, log only
    if (status && status >= 500) {
      console.error('[API Error]', error.response?.data);
      return Promise.reject(new Error('Server error, please try again later'));
    }

    // Network errors
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Request timeout, please check your connection'));
    }

    return Promise.reject(new Error('Network connection failed'));
  }
);

export default client;

/**
 * Get the current access token from localStorage
 * Used by SSE utilities that need direct token access
 */
export function getToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}
