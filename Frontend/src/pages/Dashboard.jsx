/**
 * Aurevia Dashboard Router
 * 
 * Protected route - requires authentication
 * Automatically redirects to role-specific dashboard based on user's role
 */

import { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { isTrader, isServerOwner, canManagePlatform, canAdmin, canModerate } from '../utils/permissions';

const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) return;

    // Priority order: Platform Admin > Admin > Moderator > Server Owner > Trader
    if (canManagePlatform(user)) {
      navigate('/dashboard/platform-admin', { replace: true });
    } else if (canAdmin(user)) {
      navigate('/dashboard/admin', { replace: true });
    } else if (canModerate(user)) {
      navigate('/dashboard/moderator', { replace: true });
    } else if (isServerOwner(user)) {
      navigate('/dashboard/server-owner', { replace: true });
    } else if (isTrader(user)) {
      navigate('/dashboard/trader', { replace: true });
    } else {
      // Fallback to trader dashboard for users without specific roles
      navigate('/dashboard/trader', { replace: true });
    }
  }, [user, navigate]);

  // Show loading while redirecting
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      color: '#fff'
    }}>
      <h2>Loading your dashboard...</h2>
    </div>
  );
};

export default Dashboard;
