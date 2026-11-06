/**
 * Pricing Page
 * 
 * Displays subscription plans with Stripe Checkout integration
 * 
 * SECURITY:
 * - All pricing from backend (never trust frontend)
 * - Stripe Checkout handles payment (PCI compliant)
 * - Server validates plan before creating session
 * - Handles upgrade/downgrade with proration preview
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../config/api';
import './Pricing.css';

const Pricing = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [processingPlan, setProcessingPlan] = useState(null);
  const [showProrationModal, setShowProrationModal] = useState(false);
  const [prorationData, setProrationData] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);

  const { user, isAuthenticated, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    setLoading(false); // No need to fetch plans anymore

    // Handle redirect from Stripe
    const subscription = searchParams.get('subscription');
    if (subscription === 'success') {
      setError('');
      checkAuth(); // Refresh user data
      setTimeout(() => {
        navigate('/subscription');
      }, 2000);
    } else if (subscription === 'canceled') {
      setError('Subscription checkout was canceled');
    }
  }, [isAuthenticated, checkAuth, navigate, searchParams]);

  const handleSelectPlan = async (plan) => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/pricing' } });
      return;
    }

    setProcessingPlan(plan.tier);
    setError('');

    try {
      // SECURITY: Backend validates plan and creates Stripe session
      const response = await api.post('/subscriptions/checkout/', {
        price_id: plan.stripe_price_id,
        tier: plan.tier,
      });

      // Check if confirmation required (for upgrades/downgrades)
      if (response.data.requires_confirmation) {
        setSelectedPlan(plan);
        await fetchProrationPreview(plan);
        setShowProrationModal(true);
        setProcessingPlan(null);
        return;
      }

      // Redirect to Stripe Checkout
      if (response.data.url) {
        window.location.href = response.data.url;
      } else {
        setError('Failed to create checkout session');
        setProcessingPlan(null);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start checkout');
      setProcessingPlan(null);
    }
  };

  const fetchProrationPreview = async (plan) => {
    try {
      const response = await api.post('/subscriptions/preview/', {
        price_id: plan.stripe_price_id,
        tier: plan.tier,
      });
      setProrationData(response.data);
    } catch (err) {
      console.error('Error fetching proration:', err);
      setError('Failed to calculate proration');
    }
  };

  const confirmSubscriptionChange = async () => {
    if (!selectedPlan) return;

    setProcessingPlan(selectedPlan.tier);
    setError('');

    try {
      const response = await api.post('/subscriptions/confirm/', {
        price_id: selectedPlan.stripe_price_id,
        tier: selectedPlan.tier,
      });

      if (response.data.message) {
        setShowProrationModal(false);
        await checkAuth(); // Refresh user data
        navigate('/subscription');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update subscription');
    } finally {
      setProcessingPlan(null);
      setShowProrationModal(false);
    }
  };

  const isCurrentPlan = (tier) => {
    return user?.subscription_tier === tier;
  };

  const canSelectPlan = (tier) => {
    if (tier === 'free') return false; // Can't "buy" free tier
    if (!isAuthenticated) return true;
    return !isCurrentPlan(tier);
  };

  if (loading) {
    return <div className="pricing-page loading">Loading plans...</div>;
  }

  return (
    <div className="pricing-page">
      <div className="pricing-header">
        <h1>Aurevia Access</h1>
        <p>Unlock premium analytics for your trading community</p>
      </div>

      {error && (
        <div className="pricing-error">
          {error}
        </div>
      )}

      {searchParams.get('subscription') === 'success' && (
        <div className="pricing-success">
          Subscription activated successfully! Redirecting to dashboard...
        </div>
      )}

      <div className="pricing-main-plan">
        <div className="plan-card main-plan">
          <div className="sub-plan-header">
            <h3>Aurevia Access</h3>
            <div className="plan-price">
              $150
              <span className="plan-price-period">/mo</span>
            </div>
          </div>

          <button
            onClick={() => navigate('/register')}
            disabled={!!processingPlan}
            className="plan-button primary"
          >
            {processingPlan ? 'Processing...' : 'Get Aurevia Access'}
          </button>
        </div>
      </div>

      <div className="pricing-features-grid">
        <FeatureCard
          title="Verification"
          features={[
            "Verified trader payout submissions",
            "Fraud-resistant validation process",
            "Permanent payout records",
            "Public legitimacy badge"
          ]}
        />
        <FeatureCard
          title="Leaderboards"
          features={[
            "Global leaderboard inclusion",
            "Rankings based on verified data only",
            "Historical performance tracking",
            "Equal visibility framework"
          ]}
        />
        <FeatureCard
          title="Public Server Profile"
          features={[
            "Dedicated server page",
            "About section & identity",
            "Public verified statistics",
            "Trust & milestone badges"
          ]}
        />
        <FeatureCard
          title="Private Analytics"
          features={[
            "Total verified payout volume",
            "Submission activity & growth trends",
            "Active contributor metrics",
            "Historical performance timelines",
            "Server health indicators"
          ]}
        />
        <FeatureCard
          title="Discovery & Exposure"
          features={[
            "Indexed across Aurevia",
            "Organic discovery via rankings",
            "Platform-wide visibility"
          ]}
        />
        <FeatureCard
          title="Platform Access"
          features={[
            "Continuous system updates",
            "Analytics expansion over time",
            "Standard support & verification handling"
          ]}
        />
      </div>

      {/* Proration Modal */}
      {showProrationModal && prorationData && (
        <ProrationModal
          prorationData={prorationData}
          onConfirm={confirmSubscriptionChange}
          onCancel={() => {
            setShowProrationModal(false);
            setSelectedPlan(null);
            setProrationData(null);
          }}
          isProcessing={!!processingPlan}
        />
      )}
    </div>
  );
};

const PlanCard = ({ plan, features, isCurrentPlan, canSelect, isProcessing, onSelect }) => {
  const isPopular = plan.tier === 'pro';
  const isFree = plan.tier === 'free';

  return (
    <div className={`plan-card ${isPopular ? 'popular' : ''}`}>
      {isPopular && (
        <div className="plan-badge">
          MOST POPULAR
        </div>
      )}

      {isCurrentPlan && (
        <div className="plan-badge current">
          CURRENT PLAN
        </div>
      )}

      <div className="plan-header">
        <h3>{plan.name}</h3>
        <div className="plan-price">
          ${plan.price_per_month}
          <span className="plan-price-period">/mo</span>
        </div>
        {plan.description && (
          <p className="plan-description">{plan.description}</p>
        )}
      </div>

      <ul className="plan-features">
        {features.map((feature, index) => (
          <li key={index}>
            <span className="checkmark"></span>
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <button
        onClick={onSelect}
        disabled={!canSelect || isProcessing}
        className={`plan-button ${isCurrentPlan ? 'secondary' : (isPopular ? 'primary' : 'success')}`}
      >
        {isProcessing ? 'Processing...' : (
          isCurrentPlan ? 'Current Plan' : (
            isFree ? 'Always Free' : 'Get Started'
          )
        )}
      </button>
    </div>
  );
};

const FeatureCard = ({ title, features }) => {
  return (
    <div className="feature-card">
      <div className="feature-header">
        <h4>{title}</h4>
      </div>
      <ul className="feature-list">
        {features.map((feature, index) => (
          <li key={index}>
            <span className="checkmark"></span>
            <span>{feature}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

const FeatureComparisonTable = ({ plans }) => {
  const features = [
    { name: 'Payout Submissions', starter: '✓', pro: '✓', elite: '✓' },
    { name: 'Leaderboard Access', starter: 'Top 5', pro: 'Top 10', elite: 'Top 15' },
    { name: 'Analytics Dashboard', starter: 'Basic', pro: 'Advanced', elite: 'Full Suite' },
    { name: 'Metrics Timeframes', starter: '7d/30d/90d', pro: '7d/30d/90d', elite: '7d/30d/90d' },
    { name: 'Health Score', starter: 'Overall only', pro: 'Full Breakdown', elite: 'Full Breakdown' },
    { name: 'Rank Tracking', starter: 'Current', pro: 'Progression', elite: 'Progression' },
    { name: 'Payout Timeline', starter: 'Count only', pro: 'With Events', elite: 'With Events' },
    { name: 'Support', starter: 'Email', pro: 'Priority', elite: 'Dedicated' },
  ];

  return (
    <div className="feature-comparison-table-wrapper">
      <table className="feature-comparison-table">
        <thead>
          <tr>
            <th>Feature</th>
            {plans.map(plan => (
              <th key={plan.id}>{plan.tier}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {features.map((feature, index) => (
            <tr key={index}>
              <td>{feature.name}</td>
              <td>{feature.free}</td>
              <td>{feature.starter}</td>
              <td>{feature.pro}</td>
              <td>{feature.elite}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const ProrationModal = ({ prorationData, onConfirm, onCancel, isProcessing }) => {
  const isUpgrade = prorationData.is_upgrade;

  return (
    <div className="proration-modal-overlay">
      <div className="proration-modal">
        <h2>Confirm {isUpgrade ? 'Upgrade' : 'Downgrade'}</h2>

        <div className="proration-plans">
          <div className="proration-plan-row">
            <span>Current Plan:</span>
            <strong>
              {prorationData.current_plan.tier} (${prorationData.current_plan.price}/mo)
            </strong>
          </div>

          <div className="proration-plan-row new">
            <span>New Plan:</span>
            <strong>
              {prorationData.new_plan.tier} (${prorationData.new_plan.price}/mo)
            </strong>
          </div>
        </div>

        {prorationData.proration.is_charge && (
          <div className="proration-charge">
            <p>Immediate Charge:</p>
            <p className="proration-amount">${prorationData.immediate_charge.toFixed(2)}</p>
            <p className="proration-description">
              Prorated amount for the remainder of your billing period
            </p>
          </div>
        )}

        {prorationData.proration.is_credit && (
          <div className="proration-credit">
            <p>Credit Applied:</p>
            <p className="proration-amount">${prorationData.credit_applied.toFixed(2)}</p>
            <p className="proration-description">
              Unused amount from your current plan
            </p>
          </div>
        )}

        <p className="proration-billing-date">
          Your next billing date is{' '}
          <strong>{new Date(prorationData.period_end).toLocaleDateString()}</strong>
        </p>

        <div className="proration-actions">
          <button onClick={onCancel} disabled={isProcessing} className="cancel">
            Cancel
          </button>
          <button onClick={onConfirm} disabled={isProcessing} className="confirm">
            {isProcessing ? 'Processing...' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Pricing;
