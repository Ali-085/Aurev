/**
 * Analytics Service
 * 
 * Centralizes all analytics and dashboard-related API calls
 */

import api, { publicApi } from '../config/api';

export const analyticsService = {
  // Public Server Analytics
  /**
   * Get public server analytics
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Analytics data
   */
  getPublicServerAnalytics: async (serverId) => {
    const response = await publicApi.get(`/analytics/server/${serverId}/public/`);
    return response.data;
  },

  /**
   * Get public server dashboard data (no auth required)
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Public dashboard data
   */
  getPublicServerDashboard: async (serverId) => {
    const response = await publicApi.get(`/servers/view/${serverId}/public_dashboard/`);
    return response.data;
  },

  // Server Dashboard APIs (for authenticated server members)
  /**
   * Get server dashboard data (requires member authentication)
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Dashboard data
   */
  getServerDashboard: async (serverId) => {
    const response = await api.get(`/servers/view/${serverId}/dashboard/`);
    return response.data;
  },

  /**
   * Get server leaderboard
   * @param {string} serverId - Server UUID
   * @returns {Promise<Array>} Leaderboard data
   */
  getServerLeaderboard: async (serverId) => {
    const response = await api.get(`/servers/view/${serverId}/leaderboard/`);
    return response.data;
  },

  /**
   * Get server activity heatmap
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Heatmap data
   */
  getServerHeatmap: async (serverId) => {
    const response = await api.get(`/servers/view/${serverId}/heatmap/`);
    return response.data;
  },

  /**
   * Get server screenshot gallery
   * @param {string} serverId - Server UUID
   * @returns {Promise<Array>} Gallery images
   */
  getServerGallery: async (serverId) => {
    const response = await api.get(`/servers/view/${serverId}/gallery/`);
    return response.data;
  },

  /**
   * Get server moderation statistics
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Moderation stats
   */
  getServerModerationStats: async (serverId) => {
    const response = await api.get(`/servers/view/${serverId}/moderation_stats/`);
    return response.data;
  },

  /**
   * Get global comparison data
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Comparison data
   */
  getGlobalComparison: async (serverId) => {
    const response = await api.get(`/servers/view/${serverId}/global_comparison/`);
    return response.data;
  },

  /**
   * Get trader profile data
   * @param {string} serverId - Server UUID
   * @param {number} traderId - Trader ID
   * @returns {Promise<Object>} Trader profile
   */
  getTraderProfile: async (serverId, traderId) => {
    const response = await api.get(`/servers/view/${serverId}/traders/${traderId}/`);
    return response.data;
  },

  /**
   * Get trader submissions
   * @param {string} serverId - Server UUID
   * @param {number} traderId - Trader ID
   * @returns {Promise<Array>} Trader submissions
   */
  getTraderSubmissions: async (serverId, traderId) => {
    const response = await api.get(`/servers/view/${serverId}/traders/${traderId}/submissions/`);
    return response.data;
  },

  // Server Owner Analytics
  /**
   * Get detailed server analytics for owner
   * @param {number} serverId - Server ID
   * @returns {Promise<Object>} Detailed analytics
   */
  getServerOwnerAnalytics: async (serverId) => {
    const response = await api.get(`/analytics/server-owner/${serverId}/`);
    return response.data;
  },

  // Role/Subscription Management
  /**
   * Get server subscription tiers
   * @param {string} serverId - Server UUID
   * @returns {Promise<Array>} Subscription tiers
   */
  getSubscriptionTiers: async (serverId) => {
    const response = await api.get(`/servers/view/${serverId}/subscription_tiers/`);
    return response.data;
  },

  /**
   * Subscribe to server tier
   * @param {string} serverId - Server UUID
   * @param {Object} subscriptionData - Subscription details
   * @returns {Promise<Object>} Subscription result
   */
  subscribeToTier: async (serverId, subscriptionData) => {
    const response = await api.post(`/servers/view/${serverId}/subscribe/`, subscriptionData);
    return response.data;
  },

  /**
   * Get user's subscription for a server
   * @param {number} serverId - Server ID
   * @returns {Promise<Object>} User subscription details
   */
  getUserSubscription: async (serverId) => {
    const response = await api.get(
      `/subscriptions/server-subscriptions/my_subscription/?server_id=${serverId}`
    );
    return response.data;
  },
};

export default analyticsService;
