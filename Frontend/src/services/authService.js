/**
 * Authentication Service
 * 
 * Centralizes all authentication-related API calls
 */

import api from '../config/api';

export const authService = {
  /**
   * Login user with email and password
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<Object>} User data and tokens
   */
  login: async (email, password) => {
    const response = await api.post('/auth/login/', {
      email,
      password,
    });
    return response.data;
  },

  /**
   * Register new user
   * @param {Object} userData - Registration data
   * @param {string} userData.username - Username
   * @param {string} userData.email - Email
   * @param {string} userData.password - Password
   * @param {string} userData.accountType - Account type (normal/trader/server_creator)
   * @param {string} [userData.serverId] - Server UUID (for trader accounts)
   * @param {string} [userData.tier] - Subscription tier (for server_creator accounts)
   * @param {string} [userData.serverName] - Server name (optional)
   * @param {string} [userData.serverDescription] - Server description (optional)
   * @param {string} [userData.discordServerId] - Discord server ID (optional)
   * @returns {Promise<Object>} User data
   */
  register: async ({ 
    username, 
    email, 
    password, 
    accountType = 'normal', 
    serverId = null,
    tier = null,
    serverName = '',
    serverDescription = '',
    discordServerId = ''
  }) => {
    const payload = {
      username,
      email,
      password,
      password_confirm: password,
      account_type: accountType
    };
    
    if (accountType === 'trader' && serverId) {
      payload.server_id = serverId;
    }
    
    if (accountType === 'server_creator') {
      payload.tier = tier;
      if (serverName) payload.server_name = serverName;
      if (serverDescription) payload.server_description = serverDescription;
      if (discordServerId) payload.discord_server_id = discordServerId;
    }
    
    const response = await api.post('/auth/register/', payload);
    return response.data;
  },

  /**
   * Logout current user
   * @returns {Promise<void>}
   */
  logout: async () => {
    await api.post('/auth/logout/');
  },

  /**
   * Get current user profile
   * @returns {Promise<Object>} User data
   */
  getCurrentUser: async () => {
    const response = await api.get('/auth/me/');
    return response.data;
  },

  /**
   * Refresh authentication token
   * @returns {Promise<void>}
   */
  refreshToken: async () => {
    await api.post('/auth/refresh/');
  },

  /**
   * Request password reset email
   * @param {string} email - User email
   * @returns {Promise<Object>} Success message
   */
  forgotPassword: async (email) => {
    const response = await api.post('/auth/forgot-password/', { email });
    return response.data;
  },

  /**
   * Reset password with token
   * @param {string} uid - Base64 encoded user ID
   * @param {string} token - Reset token
   * @param {string} newPassword - New password
   * @param {string} confirmPassword - Password confirmation
   * @returns {Promise<Object>} Success message
   */
  resetPassword: async (uid, token, newPassword, confirmPassword) => {
    const response = await api.post('/auth/reset-password/', {
      uid,
      token,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    return response.data;
  },

  /**
   * Change password for authenticated user
   * @param {string} currentPassword - Current password
   * @param {string} newPassword - New password
   * @param {string} confirmPassword - Password confirmation
   * @returns {Promise<Object>} Success message
   */
  changePassword: async (currentPassword, newPassword, confirmPassword) => {
    const response = await api.post('/auth/change-password/', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    return response.data;
  },
};

export default authService;
