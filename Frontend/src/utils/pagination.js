/**
 * Pagination Utility
 * 
 * Handles paginated API responses and provides helper functions
 * for working with paginated data throughout the frontend.
 */

/**
 * Extract pagination data from API response
 * @param {Object} response - Axios response object
 * @returns {Object} Object with data and pagination metadata
 */
export const handlePaginatedResponse = (response) => {
  // Check if response is paginated
  if (response.data.results !== undefined) {
    return {
      data: response.data.results,
      pagination: {
        count: response.data.count || 0,
        next: response.data.next,
        previous: response.data.previous,
        currentPage: response.data.current_page || 1,
        totalPages: response.data.total_pages || 1,
        pageSize: response.data.page_size || 20,
      }
    };
  }
  
  // Fallback for non-paginated responses
  return {
    data: response.data,
    pagination: null
  };
};

/**
 * Build query parameters for paginated request
 * @param {number} page - Page number (1-indexed)
 * @param {number} pageSize - Number of items per page
 * @param {Object} additionalParams - Additional query parameters
 * @returns {Object} Query parameters object
 */
export const buildPaginationParams = (page = 1, pageSize = 20, additionalParams = {}) => {
  return {
    page,
    page_size: pageSize,
    ...additionalParams
  };
};

/**
 * Calculate total pages from count and page size
 * @param {number} count - Total number of items
 * @param {number} pageSize - Items per page
 * @returns {number} Total number of pages
 */
export const calculateTotalPages = (count, pageSize) => {
  return Math.ceil(count / pageSize);
};

/**
 * Extract page number from next/previous URL
 * @param {string|null} url - Next or previous page URL
 * @returns {number|null} Page number or null if no URL
 */
export const extractPageNumber = (url) => {
  if (!url) return null;
  
  try {
    const urlObj = new URL(url);
    const page = urlObj.searchParams.get('page');
    return page ? parseInt(page, 10) : null;
  } catch (e) {
    return null;
  }
};

/**
 * Check if there are more pages available
 * @param {Object} pagination - Pagination metadata
 * @returns {boolean} True if more pages available
 */
export const hasNextPage = (pagination) => {
  if (!pagination) return false;
  return pagination.currentPage < pagination.totalPages;
};

/**
 * Check if there is a previous page available
 * @param {Object} pagination - Pagination metadata
 * @returns {boolean} True if previous page available
 */
export const hasPreviousPage = (pagination) => {
  if (!pagination) return false;
  return pagination.currentPage > 1;
};

/**
 * Get page range for pagination controls
 * @param {number} currentPage - Current page number
 * @param {number} totalPages - Total number of pages
 * @param {number} maxVisible - Maximum number of page buttons to show
 * @returns {Array<number>} Array of page numbers to display
 */
export const getPageRange = (currentPage, totalPages, maxVisible = 5) => {
  if (totalPages <= maxVisible) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  
  const halfVisible = Math.floor(maxVisible / 2);
  let startPage = Math.max(1, currentPage - halfVisible);
  let endPage = Math.min(totalPages, startPage + maxVisible - 1);
  
  // Adjust start if we're near the end
  if (endPage - startPage < maxVisible - 1) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }
  
  return Array.from({ length: endPage - startPage + 1 }, (_, i) => startPage + i);
};

/**
 * Page size options for dropdown
 */
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

/**
 * Default page size
 */
export const DEFAULT_PAGE_SIZE = 20;
