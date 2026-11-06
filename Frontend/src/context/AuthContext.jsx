/**
 * Authentication Context
 * 
 * SECURITY:
 * - Secure token storage (httpOnly cookies preferred, localStorage as fallback)
 * - Token refresh handling
 * - Role-based access control
 * - Automatic logout on token expiry
 */

import { createContext, useState, useEffect, useContext } from 'react';
import { authService } from '../services';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // SECURITY: Check authentication status on mount and route changes
  useEffect(() => {
    let isMounted = true;
    
    // Check if current page is public (should not show loading)
    const pathname = window.location.pathname;
    const isPublicPage = pathname === '/login' || 
                         pathname === '/register' ||
                         pathname === '/verify-notice' ||
                         pathname.startsWith('/verify') ||
                         pathname === '/' ||
                         pathname === '/analytics' ||
                         pathname === '/pricing' ||
                         pathname === '/servers' ||
                         pathname === '/unauthorized' ||
                         pathname === '/forgot-password' ||
                         pathname.startsWith('/reset-password');
    
    const checkAuthSafe = async () => {
      try {
        // SECURITY: Token is in HttpOnly cookie, automatically sent
        // Verify token is valid by fetching user profile
        const userData = await authService.getCurrentUser();
        if (isMounted) {
          setUser(userData);
          setIsAuthenticated(true);
        }
      } catch (error) {
        // Token invalid, expired, or not present
        if (isMounted) {
          setUser(null);
          setIsAuthenticated(false);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    
    // Always check auth status in background, but don't show loading on public pages
    if (isPublicPage) {
      setLoading(false); // Don't show loading on public pages
      checkAuthSafe(); // Still check auth in background for components that need it
    } else {
      setLoading(true); // Show loading on protected pages
      checkAuthSafe();
    }
    
    // Cleanup: prevent state updates after unmount
    return () => {
      isMounted = false;
    };
  }, [window.location.pathname]);

  const checkAuth = async () => {
    try {
      // SECURITY: Token is in HttpOnly cookie, automatically sent
      // Verify token is valid by fetching user profile
      const userData = await authService.getCurrentUser();
      setUser(userData);
      setIsAuthenticated(true);
    } catch (error) {
      // Token invalid, expired, or not present
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const data = await authService.login(username, password);
      const { user: userData, pending_payment, application_id, redirect_to } = data;
      
      // SECURITY: Tokens are in HttpOnly cookies (set by backend)
      // No localStorage needed - cookies are automatically sent with requests
      setUser(userData);
      setIsAuthenticated(true);

      return { 
        success: true, 
        user: userData,
        pending_payment,
        application_id,
        redirect_to
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.response?.data?.error || 'Login failed',
      };
    }
  };

  const register = async (
    username, 
    email, 
    password, 
    accountType = 'normal', 
    serverId = null,
    tier = null,
    serverName = '',
    serverDescription = '',
    discordServerId = ''
  ) => {
    try {
      const data = await authService.register({
        username,
        email,
        password,
        accountType,
        serverId,
        tier,
        serverName,
        serverDescription,
        discordServerId
      });

      const { user: userData } = data;
      // SECURITY: Tokens are in HttpOnly cookies (set by backend)
      
      setUser(userData);
      setIsAuthenticated(true);

      return { success: true };
    } catch (error) {
      console.error('Registration error:', error.response?.data);
      
      // Handle different error formats
      const data = error.response?.data;
      let errorMessage = 'Registration failed';
      
      if (data) {
        // Check for field-specific errors (array format)
        if (data.password?.[0]) errorMessage = `Password: ${data.password[0]}`;
        else if (data.username?.[0]) errorMessage = `Username: ${data.username[0]}`;
        else if (data.email?.[0]) errorMessage = `Email: ${data.email[0]}`;
        else if (data.account_type?.[0]) errorMessage = `Account type: ${data.account_type[0]}`;
        else if (data.server_id?.[0]) errorMessage = `Server: ${data.server_id[0]}`;
        // Check for non_field_errors
        else if (data.non_field_errors?.[0]) errorMessage = data.non_field_errors[0];
        // Check for simple error message
        else if (data.error) errorMessage = data.error;
        else if (data.detail) errorMessage = data.detail;
      }
      
      return {
        success: false,
        error: errorMessage,
      };
    }
  };

  const logout = async () => {
    try {
      // SECURITY: Call logout endpoint to clear HttpOnly cookies
      await authService.logout();
    } catch (error) {
      // Continue with local logout even if API call fails
      console.error('Logout API error:', error);
    }

    // Clear local auth state (cookies cleared by backend)
    setUser(null);
    setIsAuthenticated(false);
  };

  const fetchUser = async () => {
    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
      setIsAuthenticated(true);
      return userData;
    } catch (error) {
      console.error('Error fetching user:', error);
      setUser(null);
      setIsAuthenticated(false);
      return null;
    }
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
    checkAuth,
    fetchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
