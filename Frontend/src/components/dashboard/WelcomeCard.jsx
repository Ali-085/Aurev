import { useAuth } from '../../context/AuthContext';
import { isPlatformStaff } from '../../utils/permissions';
import './WelcomeCard.css';

const WelcomeCard = ({ customGreeting, showBadges = true }) => {
  const { user } = useAuth();
  const isStaff = isPlatformStaff(user);

  return (
    <div className="welcome-card">
      <div className="welcome-content">
        <h2>{customGreeting || `Welcome Home, ${user?.username}!`}</h2>
        <p className="welcome-email">{user?.email}</p>
        {showBadges && (
          <div className="welcome-badges">
            {user?.subscription_tier && user.subscription_tier !== 'free' && (
              <span className="badge badge-primary">{user.subscription_tier}</span>
            )}
            {isStaff && <span className="badge badge-success">Platform Staff</span>}
          </div>
        )}
      </div>
    </div>
  );
};

export default WelcomeCard;
