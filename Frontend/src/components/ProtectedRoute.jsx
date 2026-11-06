/**
 * Protected Route Component
 * 
 * SECURITY:
 * - Prevents unauthorized access to protected routes
 * - Redirects to login if not authenticated
 * - Role-based access control
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { hasCapability, hasAnyCapability } from '../utils/permissions';

const ProtectedRoute = ({ children, requiredCapability = null, requiredCapabilities = null, requiresSuperuser = false }) => {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  // Show loading state while checking auth
  if (loading) {
    return <div>Loading...</div>;
  }

  // SECURITY: Not authenticated - redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // SECURITY: Check platform access
  if (requiresSuperuser && !hasCapability(user, 'can_access_platform')) {
    return <Navigate to="/unauthorized" replace />;
  }

  // SECURITY: Check capability-based access
  if (requiredCapability && !hasCapability(user, requiredCapability)) {
    return <Navigate to="/unauthorized" replace />;
  }

  if (requiredCapabilities && !hasAnyCapability(user, requiredCapabilities)) {
    return <Navigate to="/unauthorized" replace />;
  }

  // Authorized - render children
  return children;
};

export default ProtectedRoute;
