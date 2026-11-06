/**
 * Payout Service
 * 
 * Centralizes all payout submission and review-related API calls
 */

import api from '../config/api';

export const payoutService = {
  /**
   * Submit new payout
   * @param {FormData} formData - Payout data (supports file uploads)
   * @returns {Promise<Object>} Submission result
   */
  submitPayout: async (formData) => {
    const response = await api.post('/payouts/submissions/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Get user's payout submissions
   * @returns {Promise<Array>} User's submissions
   */
  getMySubmissions: async () => {
    const response = await api.get('/payouts/my-submissions/');
    return response.data;
  },

  /**
   * Get single submission details
   * @param {number} submissionId - Submission ID
   * @returns {Promise<Object>} Submission details
   */
  getSubmission: async (submissionId) => {
    const response = await api.get(`/payouts/submissions/${submissionId}/`);
    return response.data;
  },

  /**
   * Update submission
   * @param {number} submissionId - Submission ID
   * @param {FormData} formData - Updated submission data
   * @returns {Promise<Object>} Updated submission
   */
  updateSubmission: async (submissionId, formData) => {
    const response = await api.patch(`/payouts/submissions/${submissionId}/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Delete submission
   * @param {number} submissionId - Submission ID
   * @returns {Promise<void>}
   */
  deleteSubmission: async (submissionId) => {
    await api.delete(`/payouts/submissions/${submissionId}/`);
  },

  /**
   * Review payout submission (approve/reject)
   * @param {number} submissionId - Submission ID
   * @param {Object} reviewData - Review decision and notes
   * @param {string} reviewData.action - 'approve' or 'reject'
   * @param {string} [reviewData.notes] - Review notes
   * @returns {Promise<Object>} Review result
   */
  reviewSubmission: async (submissionId, reviewData) => {
    const response = await api.post(`/payouts/submissions/${submissionId}/review/`, reviewData);
    return response.data;
  },

  /**
   * Flag submission as suspicious
   * @param {number} submissionId - Submission ID
   * @param {Object} flagData - Flag reason
   * @returns {Promise<Object>} Flag result
   */
  flagSubmission: async (submissionId, flagData) => {
    const response = await api.post(`/payouts/submissions/${submissionId}/flag/`, flagData);
    return response.data;
  },

  /**
   * Get pending submissions for review (moderator)
   * @returns {Promise<Array>} Pending submissions
   */
  getPendingSubmissions: async () => {
    const response = await api.get('/payouts/pending/');
    return response.data;
  },

  /**
   * Get flagged submissions (moderator/admin)
   * @returns {Promise<Array>} Flagged submissions
   */
  getFlaggedSubmissions: async () => {
    const response = await api.get('/payouts/flagged/');
    return response.data;
  },
};

export default payoutService;
