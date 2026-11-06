/**
 * Server Creator Checkout Page
 * 
 * SECURITY:
 * - Requires authentication (protected route)
 * - Uses centralized API with CSRF protection
 * - Redirects to Stripe hosted checkout (PCI compliant)
 * - Tier validation happens server-side
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { createCheckoutSession } from '../services/serverCreatorService';
import { useAuth } from '../context/AuthContext';
import api from '../config/api';
import './ServerCreatorCheckout.css';

export default function ServerCreatorCheckout() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const navigate = useNavigate();
  const { user, fetchUser } = useAuth();

  // Poll for payment completion every 3 seconds
  useEffect(() => {
    let pollInterval;

    const checkPaymentStatus = async () => {
      try {
        const response = await api.get('/subscriptions/server-creator/status/');
        
        // If payment completed, refresh user data and redirect
        if (response.data.status === 'completed' || !response.data.pending_payment) {
          clearInterval(pollInterval);
          
          // Refresh user data to get new role
          if (fetchUser) {
            await fetchUser();
          }
          
          navigate('/dashboard', { replace: true });
        }
      } catch (err) {
        console.error('Error checking payment status:', err);
      } finally {
        setCheckingStatus(false);
      }
    };

    // Initial check
    checkPaymentStatus();

    // Poll every 3 seconds
    pollInterval = setInterval(checkPaymentStatus, 3000);

    // Cleanup
    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [navigate, fetchUser]);

  const handleCheckout = async () => {
    setLoading(true);
    setError(null);

    try {
      // Call backend to create Stripe checkout session
      const { url } = await createCheckoutSession();
      
      // Redirect to Stripe's hosted checkout page
      window.location.href = url;
      
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create checkout session');
      setLoading(false);
    }
  };

  return (
    <div className="checkout-container">
      <div className="checkout-card">
        <h1>Complete Your Server Creator Registration</h1>
        <p className="subtitle">You're one step away from creating your server!</p>
        
        <div className="checkout-info">
          <p>Email verified</p>
          <p>Payment required to activate account</p>
        </div>

        {error && (
          <div className="error-message">
            <span className="error-icon"></span>
            {error}
          </div>
        )}
        
        <button 
          onClick={handleCheckout} 
          disabled={loading}
          className="checkout-button"
        >
          {loading ? 'Redirecting to Stripe...' : 'Proceed to Payment'}
        </button>
        
        <div className="security-info">
          <div className="security-badge">
            <span>Secured by Stripe</span>
          </div>
          <div className="security-badge">
            <span>All major cards accepted</span>
          </div>
        </div>

        <p className="note">
          Your registration will expire in 24 hours if payment is not completed.
        </p>

        <button 
          onClick={() => navigate('/dashboard')}
          className="cancel-button"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
