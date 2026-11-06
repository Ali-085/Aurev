/**
 * Admin Service
 * 
 * Centralizes all admin and moderator dashboard-related API calls
 */

import api from '../config/api';

export const adminService = {
  // Admin Dashboard APIs
  /**
   * Get admin dashboard overview
   * @returns {Promise<Object>} Dashboard overview data
   */
  getAdminOverview: async () => {
    const response = await api.get('/platform-admin/admin-dashboard/overview/');
    return response.data;
  },

  /**
   * Get pending submissions for admin review
   * @returns {Promise<Array>} Pending submissions
   */
  getAdminPendingSubmissions: async () => {
    const response = await api.get('/platform-admin/admin-dashboard/pending_submissions/');
    return response.data;
  },

  /**
   * Get suspicious submissions
   * @returns {Promise<Array>} Suspicious submissions
   */
  getAdminSuspiciousSubmissions: async () => {
    const response = await api.get('/platform-admin/admin-dashboard/suspicious_submissions/');
    return response.data;
  },

  /**
   * Get server list for admin
   * @returns {Promise<Array>} All servers
   */
  getAdminServerList: async () => {
    const response = await api.get('/platform-admin/admin-dashboard/server_list/');
    return response.data;
  },

  /**
   * Get server analytics (admin)
   * @param {string} serverId - Server UUID
   * @returns {Promise<Object>} Server analytics
   */
  getAdminServerAnalytics: async (serverId) => {
    const response = await api.get(`/platform-admin/admin-dashboard/${serverId}/server_analytics/`);
    return response.data;
  },

  /**
   * Pause server submissions
   * @param {number} serverId - Server ID
   * @param {Object} data - Pause reason
   * @returns {Promise<Object>} Result
   */
  pauseServerSubmissions: async (serverId, data = {}) => {
    const response = await api.post(
      `/platform-admin/admin-dashboard/${serverId}/pause_server_submissions/`,
      data
    );
    return response.data;
  },

  /**
   * Resume server submissions
   * @param {number} serverId - Server ID
   * @param {Object} data - Resume notes
   * @returns {Promise<Object>} Result
   */
  resumeServerSubmissions: async (serverId, data = {}) => {
    const response = await api.post(
      `/platform-admin/admin-dashboard/${serverId}/resume_server_submissions/`,
      data
    );
    return response.data;
  },

  /**
   * Download admin report
   * @param {string} reportType - Type of report
   * @returns {Promise<Blob>} Report file
   */
  downloadReport: async (reportType) => {
    const response = await api.get(
      `/platform-admin/admin-dashboard/download_report/?report_type=${reportType}`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  // Moderator Dashboard APIs
  /**
   * Get moderator dashboard overview
   * @returns {Promise<Object>} Dashboard overview data
   */
  getModeratorOverview: async () => {
    const response = await api.get('/platform-admin/moderator-dashboard/overview/');
    return response.data;
  },

  /**
   * Get review queue for moderator
   * @returns {Promise<Array>} Submissions in review queue
   */
  getModeratorReviewQueue: async () => {
    const response = await api.get('/platform-admin/moderator-dashboard/review_queue/');
    return response.data;
  },

  /**
   * Get moderator's past reviews
   * @returns {Promise<Array>} Past reviews
   */
  getModeratorMyReviews: async () => {
    const response = await api.get('/platform-admin/moderator-dashboard/my_reviews/');
    return response.data;
  },

  /**
   * Get submission detail for moderator review
   * @param {number} submissionId - Submission ID
   * @returns {Promise<Object>} Submission details
   */
  getModeratorSubmissionDetail: async (submissionId) => {
    const response = await api.get(
      `/platform-admin/moderator-dashboard/${submissionId}/submission_detail/`
    );
    return response.data;
  },

  // User Management
  /**
   * Get all users (admin)
   * @returns {Promise<Array>} All users
   */
  getAllUsers: async () => {
    const response = await api.get('/platform-admin/users/');
    return response.data;
  },

  /**
   * Get user details (admin)
   * @param {number} userId - User ID
   * @returns {Promise<Object>} User details
   */
  getUserDetails: async (userId) => {
    const response = await api.get(`/platform-admin/users/${userId}/`);
    return response.data;
  },

  /**
   * Update user (admin)
   * @param {number} userId - User ID
   * @param {Object} userData - Updated user data
   * @returns {Promise<Object>} Updated user
   */
  updateUser: async (userId, userData) => {
    const response = await api.patch(`/platform-admin/users/${userId}/`, userData);
    return response.data;
  },

  /**
   * Ban/suspend user (admin)
   * @param {number} userId - User ID
   * @param {Object} data - Ban reason and duration
   * @returns {Promise<Object>} Result
   */
  banUser: async (userId, data) => {
    const response = await api.post(`/platform-admin/users/${userId}/ban/`, data);
    return response.data;
  },

  /**
   * Unban user (admin)
   * @param {number} userId - User ID
   * @returns {Promise<Object>} Result
   */
  unbanUser: async (userId) => {
    const response = await api.post(`/platform-admin/users/${userId}/unban/`);
    return response.data;
  },

  // Paginated API calls
  /**
   * Get all servers with pagination (admin)
   * @param {number} page - Page number
   * @param {number} pageSize - Items per page
   * @param {Object} filters - Filter parameters (search, filter)
   * @returns {Promise<Object>} Paginated servers with metadata
   */
  getServers: async (page = 1, pageSize = 20, filters = {}) => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      ...filters
    });
    const response = await api.get(`/platform-admin/servers/?${params}`);
    return response.data;
  },

  /**
   * Get all payouts with pagination (admin)
   * @param {number} page - Page number
   * @param {number} pageSize - Items per page
   * @param {Object} filters - Filter parameters (status, server, market, etc.)
   * @returns {Promise<Object>} Paginated payouts with metadata
   */
  getPayouts: async (page = 1, pageSize = 20, filters = {}) => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      ...filters
    });
    const response = await api.get(`/platform-admin/payouts/?${params}`);
    return response.data;
  },
};

export default adminService;
