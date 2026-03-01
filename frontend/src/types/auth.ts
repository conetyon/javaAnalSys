/**
 * Authentication related types
 */

// Login request
export interface LoginRequest {
  username: string;
  password: string;
}

// Registration request
export interface RegisterRequest {
  username: string;
  password: string;
  email?: string;
}

// Token response from API
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user?: UserInfo;  // Included in login response
}

// User information
export interface UserInfo {
  id: number;
  username: string;
  email?: string | null;
  role: string;
}

// Auth context state
export interface AuthState {
  isAuthenticated: boolean;
  user: UserInfo | null;
  loading: boolean;
}
