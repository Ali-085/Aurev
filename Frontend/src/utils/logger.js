/**
 * Logging Utility
 * 
 * Provides environment-aware logging that:
 * - Only logs debug info in development
 * - Always logs errors (for production debugging)
 * - Prevents console spam in production
 */

const isDev = import.meta.env.DEV;

export const logger = {
  /**
   * Log general information (development only)
   */
  log: (...args) => {
    if (isDev) {
      console.log(...args);
    }
  },

  /**
   * Log errors (always logged for production debugging)
   */
  error: (...args) => {
    console.error(...args);
  },

  /**
   * Log warnings (development only)
   */
  warn: (...args) => {
    if (isDev) {
      console.warn(...args);
    }
  },

  /**
   * Log debug information (development only)
   */
  debug: (...args) => {
    if (isDev) {
      console.debug(...args);
    }
  },

  /**
   * Log information messages (development only)
   */
  info: (...args) => {
    if (isDev) {
      console.info(...args);
    }
  },
};

export default logger;
