/**
 * Market Categories Service
 * 
 * Provides utility functions for fetching and managing market categories.
 * Markets are dynamically configurable by platform owners.
 */

import { publicApi } from '../config/api';

// Default market colors for display
export const DEFAULT_MARKET_COLORS = {
  'Futures': '#007bff',
  'Forex': '#28a745',
  'Crypto': '#ffc107',
  'Options': '#17a2b8',
  'Equities': '#6c757d',
};

// Default market icons for display
export const DEFAULT_MARKET_ICONS = {
  'Futures': '',
  'Forex': '',
  'Crypto': '',
  'Options': '',
  'Equities': '',
};

/**
 * Fetch active market categories from the platform
 * @param {boolean} includeInactive - Include inactive markets (admin only)
 * @returns {Promise<Array>} Array of market category objects
 */
export const fetchMarketCategories = async (includeInactive = false) => {
  try {
    const response = await publicApi.get('/platform-admin/markets/');
    let markets = response.data.markets || [];
    
    if (!includeInactive) {
      markets = markets.filter(m => m.is_active);
    }
    
    return markets;
  } catch (error) {
    console.error('Error fetching market categories:', error);
    
    // Fallback to default markets if API fails
    return [
      { id: 1, name: 'Futures', icon: '', is_active: true, display_order: 1 },
      { id: 2, name: 'Forex', icon: '', is_active: true, display_order: 2 },
      { id: 3, name: 'Crypto', icon: '', is_active: true, display_order: 3 },
      { id: 4, name: 'Options', icon: '', is_active: true, display_order: 4 },
      { id: 5, name: 'Equities', icon: '', is_active: true, display_order: 5 },
    ];
  }
};

/**
 * Get color for a market (with fallback)
 * @param {string} marketName - Name of the market
 * @returns {string} Hex color code
 */
export const getMarketColor = (marketName) => {
  return DEFAULT_MARKET_COLORS[marketName] || '#6c757d';
};

/**
 * Get icon for a market (with fallback)
 * @param {string} marketName - Name of the market
 * @returns {string} Icon
 */

/**
 * Get market by name from a list
 * @param {Array} markets - Array of market objects
 * @param {string} name - Market name
 * @returns {Object|null} Market object or null
 */
export const getMarketByName = (markets, name) => {
  return markets.find(m => m.name === name) || null;
};

// Export marketService object for consistent usage
export const marketService = {
  getMarketCategories: fetchMarketCategories,
  getMarketColor,
  getMarketByName
};

export default marketService;
