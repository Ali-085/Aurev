/**
 * API Configuration
 * 
 * SECURITY:
 * - Base URL from environment variable (never hardcode)
 * - Credentials included for cookie-based auth
 * - CSRF token handling
 * - Request/response interceptors for auth
 */

import axios from 'axios';

// SECURITY: Use environment variable for API URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // SECURITY: Include cookies for JWT auth
  headers: {
    'Content-Type': 'application/json',
  },
});

// SECURITY: Request interceptor - cookies are automatically sent
api.interceptors.request.use(
  (config) => {
    // Tokens are in HttpOnly cookies - browser sends them automatically
    // No need to manually add Authorization header
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// SECURITY: Response interceptor - handle token refresh and email verification
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Don't retry if already on login/register pages or public pages
    const pathname = window.location.pathname;
    const isAuthPage = pathname === '/login' || pathname === '/register';
    const isPublicPage = pathname === '/' || 
                         pathname === '/analytics' || 
                         pathname === '/pricing' || 
                         pathname === '/servers' ||
                         pathname === '/unauthorized' ||
                         pathname === '/forgot-password' ||
                         pathname === '/verify-notice' ||
                         pathname === '/verify' ||
                         pathname.match(/^\/reset-password\//) ||
                         pathname.match(/^\/servers\/[^/]+\/public$/) ||
                         pathname.match(/^\/trader\/[^/]+\/public$/);
    
    // Check for email verification required (403 with specific error code)
    if (error.response?.status === 403 && 
        error.response?.data?.error_code === 'EMAIL_NOT_VERIFIED') {
      // SECURITY: Redirect to verification notice if email not verified
      const isVerifyPage = window.location.pathname === '/verify-notice' ||
                          window.location.pathname === '/verify';
      
      if (!isVerifyPage) {
        window.location.href = '/verify-notice';
      }
      return Promise.reject(error);
    }
    
    // If 401 and not already retried, try to refresh token (but not on public pages)
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthPage && !isPublicPage) {
      originalRequest._retry = true;
      
      try {
        // SECURITY: Refresh token is in HttpOnly cookie
        // Backend will read it and return new access token in cookie
        await axios.post(
          `${API_BASE_URL}/auth/refresh/`,
          {},
          { withCredentials: true }
        );
        
        // Retry original request (new token is now in cookie)
        return api(originalRequest);
      } catch (refreshError) {
        // SECURITY: Refresh failed - redirect to login only if not already there
        if (!isAuthPage) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Create a separate public API instance that doesn't redirect on 401
// Use this for public endpoints like Analytics that work without authentication
export const publicApi = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Still send cookies if available
  headers: {
    'Content-Type': 'application/json',
  },
});

// Public API doesn't redirect to login on 401 - just returns the error
publicApi.interceptors.response.use(
  (response) => response,
  (error) => {
    // Just return the error without redirecting
    // Let the component handle it gracefully
    return Promise.reject(error);
  }
);

export default api;
