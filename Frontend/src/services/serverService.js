/**
 * Server Service
 * 
 * Centralizes all server-related API calls
 */

import api, { publicApi } from '../config/api';

export const serverService = {
  /**
   * Get all servers (public leaderboard)
   * @returns {Promise<Array>} List of servers
   */
  getAllServers: async () => {
    const response = await publicApi.get('/servers/');
    return response.data;
  },

  /**
   * Get single server by UUID
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Server data
   */
  getServerById: async (serverId) => {
    const response = await publicApi.get(`/servers/${serverId}/`);
    return response.data;
  },



  /**
   * Get servers owned by current user
   * @returns {Promise<Object>} User's servers
   */
  getMyServers: async () => {
    const response = await api.get('/servers/members/my_servers/');
    return response.data;
  },

  /**
   * Get servers owned by current user (for server owner dashboard)
   * @returns {Promise<Object>} Owner's servers
   */
  getOwnedServers: async () => {
    const response = await api.get('/analytics/server-owner/servers/');
    return response.data;
  },

  /**
   * Create new server
   * @param {Object} serverData - Server creation data
   * @returns {Promise<Object>} Created server
   */
  createServer: async (serverData) => {
    const response = await api.post('/servers/', serverData);
    return response.data;
  },

  /**
   * Update server details
   * @param {string} serverId - Server UUID
   * @param {Object|FormData} serverData - Updated server data (supports file uploads)
   * @returns {Promise<Object>} Updated server
   */
  updateServer: async (serverId, serverData) => {
    const config = serverData instanceof FormData ? {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    } : {};
    
    const response = await api.patch(`/servers/${serverId}/`, serverData, config);
    return response.data;
  },

  /**
   * Delete server
   * @param {string} serverId - Server UUID
   * @returns {Promise<void>}
   */
  deleteServer: async (serverId) => {
    await api.delete(`/servers/${serverId}/`);
  },

  // Server Branding APIs
  /**
   * Get server branding settings
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Branding data
   */
  getServerBranding: async (serverId) => {
    const response = await api.get(`/servers/${serverId}/branding/`);
    return response.data;
  },

  /**
   * Update server branding
   * @param {number} serverId - Server ID
   * @param {FormData} formData - Branding data (supports file uploads)
   * @returns {Promise<Object>} Updated branding
   */
  updateServerBranding: async (serverId, formData) => {
    const response = await api.patch(`/servers/${serverId}/branding/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Delete branding asset (logo, banner, etc)
   * @param {number} serverId - Server ID
   * @param {Object} data - Asset type to delete
   * @returns {Promise<Object>} Updated branding
   */
  deleteBrandingAsset: async (serverId, data) => {
    const response = await api.patch(`/servers/${serverId}/branding/`, data);
    return response.data;
  },

  // Server Subscription Check
  /**
   * Get server subscription info
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Subscription data
   */
  getServerSubscription: async (serverId) => {
    const response = await api.get(`/subscriptions/server/${serverId}/subscription/`);
    return response.data;
  },

  // Server Membership APIs
  /**
   * Check user membership status for a server
   * @param {string} serverId - Server ID
   * @returns {Promise<Object>} Membership status
   */
  checkMembership: async (serverId) => {
    const response = await api.get(`/servers/view/${serverId}/check_membership/`);
    return response.data;
  },

  /**
   * Join a server
   * @param {string} serverId - Server ID
   * @returns {Promise<Object>} Join result
   */
  joinServer: async (serverId) => {
    const response = await api.post(`/servers/view/${serverId}/join_server/`, {});
    return response.data;
  },

  /**
   * Leave a server
   * @param {string} serverId - Server ID
   * @returns {Promise<Object>} Leave result
   */
  leaveServer: async (serverId) => {
    const response = await api.post(`/servers/${serverId}/leave/`, {});
    return response.data;
  },
};

export default serverService;
