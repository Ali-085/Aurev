/**
 * Permission Utilities
 * 
 * SECURITY: Capability-based authorization system.
 * The backend returns ONLY what users can do (capabilities), never their
 * internal role names or privilege hierarchy. This prevents privilege
 * escalation attacks and information disclosure.
 * 
 * All permission checks use user.permissions object from backend.
 */

/**
 * Check if user has a specific capability
 * @param {Object} user - User object from auth context
 * @param {string} capability - Capability key (e.g., 'can_create_content', 'can_review_content')
 * @returns {boolean}
 */
export const hasCapability = (user, capability) => {
  if (!user || !user.permissions) return false;
  return user.permissions[capability] === true;
};

/**
 * Check if user has any of the specified capabilities
 * @param {Object} user - User object from auth context
 * @param {string[]} capabilities - Array of capability keys
 * @returns {boolean}
 */
export const hasAnyCapability = (user, capabilities) => {
  if (!user || !user.permissions) return false;
  return capabilities.some(cap => user.permissions[cap] === true);
};

/**
 * Check if user has all of the specified capabilities
 * @param {Object} user - User object from auth context
 * @param {string[]} capabilities - Array of capability keys
 * @returns {boolean}
 */
export const hasAllCapabilities = (user, capabilities) => {
  if (!user || !user.permissions) return false;
  return capabilities.every(cap => user.permissions[cap] === true);
};

/**
 * Capability checks (convenience functions for common checks)
 * Uses generic names that don't reveal internal privilege structure
 */

// Content creation capabilities
export const canCreateServer = (user) => hasCapability(user, 'can_create_content');

// Content management capabilities (generic names)
export const canModerate = (user) => hasCapability(user, 'can_review_content');
export const canAdmin = (user) => hasCapability(user, 'can_manage_content');
export const canManagePlatform = (user) => hasCapability(user, 'can_access_platform');

// Relationship-based status
export const isTrader = (user) => hasCapability(user, 'is_member');
export const isServerOwner = (user) => hasCapability(user, 'is_creator');

// Generic staff check (any type of elevated access)
export const isPlatformStaff = (user) => hasCapability(user, 'has_elevated_access');

/**
 * Legacy compatibility layer (DEPRECATED - remove after migration)
 * These map old role-based checks to new capability-based system
 */
export const hasPermission = hasCapability;
export const hasAnyPermission = hasAnyCapability;
export const hasAllPermissions = hasAllCapabilities;
