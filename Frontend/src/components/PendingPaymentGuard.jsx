/**
 * Route Protection Component
 * Redirects users with pending payments to checkout page
 */

import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../config/api';

export default function PendingPaymentGuard({ children }) {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const checkPendingPayment = async () => {
      // Only check for authenticated users
      if (!isAuthenticated || !user) {
        return;
      }
      
      // Don't redirect if already on checkout page or success/cancel pages
      if (location.pathname === '/server-creator/checkout' || 
          location.pathname === '/server-creator/success' ||
          location.pathname === '/server-creator/cancel') {
        return;
      }
      
      // Don't redirect if user has roles (they've completed payment)
      if (user.roles && user.roles.length > 0) {
        return;
      }

      try {
        // Check backend for pending payment status
        const response = await api.get('/subscriptions/server-creator/status/');
        
        console.log('PendingPaymentGuard: Status response:', response.data);
        
        if (response.data.pending_payment) {
          navigate('/server-creator/checkout', { 
            replace: true,
            state: { application_id: response.data.application_id }
          });
        }
      } catch (error) {
        // If endpoint doesn't exist or errors, don't block navigation
        console.error('PendingPaymentGuard: Error checking pending payment:', error);
      }
    };

    checkPendingPayment();
  }, [isAuthenticated, user, location.pathname, navigate]);

  return children;
}
