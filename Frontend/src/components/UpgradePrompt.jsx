/**
 * UpgradePrompt Component
 * 
 * Shows when users try to access tier-locked features.
 * Displays what tier is needed and redirects to pricing.
 */

import { useNavigate } from 'react-router-dom';
import { getTierInfo } from '../utils/tierUtils';
import './UpgradePrompt.css';

const UpgradePrompt = ({ requiredTier, featureName, inline = false }) => {
  const navigate = useNavigate();
  const tierInfo = getTierInfo(requiredTier);
  
  const handleUpgrade = () => {
    navigate('/pricing');
  };
  
  if (inline) {
    return (
      <div className="upgrade-prompt-inline">
        <span className="lock-icon">🔒</span>
        <span className="upgrade-text">
          {tierInfo.icon} {tierInfo.name} required
        </span>
        <button onClick={handleUpgrade} className="btn-upgrade-small">
          Upgrade
        </button>
      </div>
    );
  }
  
  return (
    <div className="upgrade-prompt-card" style={{ borderColor: tierInfo.color }}>
      <div className="upgrade-icon" style={{ color: tierInfo.color }}>
        🔒
      </div>
      <h3 className="upgrade-title">
        Upgrade to {tierInfo.icon} {tierInfo.name}
      </h3>
      <p className="upgrade-description">
        {featureName} is available with {tierInfo.name} tier
      </p>
      <div className="upgrade-price">{tierInfo.price}</div>
      <button onClick={handleUpgrade} className="btn-upgrade" style={{ backgroundColor: tierInfo.color }}>
        View Plans & Upgrade
      </button>
      <p className="upgrade-footer">{tierInfo.description}</p>
    </div>
  );
};

export default UpgradePrompt;
