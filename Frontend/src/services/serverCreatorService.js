/**
 * Server Creator Service
 * Handles all Server Creator registration and payment operations
 */

import api from '../config/api';

/**
 * Create Stripe checkout session for server creator payment
 * @returns {Promise<{url: string}>} Stripe checkout URL
 */
export const createCheckoutSession = async () => {
  const response = await api.post('/subscriptions/server-creator/checkout/');
  return response.data;
};

/**
 * Get current user's activation status
 * @returns {Promise<{is_active: boolean, email_verified: boolean, ...}>}
 */
export const getUserStatus = async () => {
  const response = await api.get('/auth/me/');
  return response.data;
};

/**
 * Poll user activation status until active or timeout
 * @param {number} maxAttempts - Maximum polling attempts (default 30)
 * @param {number} intervalMs - Polling interval in milliseconds (default 2000)
 * @returns {Promise<boolean>} True if activated, false if timeout
 */
export const pollActivationStatus = async (maxAttempts = 30, intervalMs = 2000) => {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(resolve => setTimeout(resolve, intervalMs));
    
    try {
      const user = await getUserStatus();
      if (user.is_active) {
        return true;
      }
    } catch (err) {
      console.error('Polling attempt failed:', err);
    }
  }
  
  return false; // Timeout
};
