import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { canAdmin, canModerate, isServerOwner, isTrader } from '../../utils/permissions';
import DashboardHeader from '../../components/dashboard/DashboardHeader';
import WelcomeCard from '../../components/dashboard/WelcomeCard';
import NavCard from '../../components/dashboard/NavCard';
import './TraderDashboard.css';

const TraderDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  // Check if user is a member of any server
  const isMember = isTrader(user);

  // Redirect users with elevated roles to their appropriate dashboards
  useEffect(() => {
    if (!user) return;
    
    if (canAdmin(user)) {
      navigate('/dashboard/admin', { replace: true });
    } else if (canModerate(user)) {
      navigate('/dashboard/moderator', { replace: true });
    } else if (isServerOwner(user)) {
      navigate('/dashboard/server-owner', { replace: true });
    }
  }, [user, navigate]);

  return (
    <div className="dashboard-container">
      <DashboardHeader />
      <WelcomeCard />
      
      <div className="nav-grid">
        {isMember && (
          <NavCard 
            title="My Servers" 
            link="/joined-servers"
            description="View servers you've joined"
          />
        )}
        <NavCard 
          title="My Profile" 
          link="/profile"
          description="View your trading profile"
        />
        {isMember && (
          <NavCard 
            title="Submit Payout" 
            link="/payouts"
            description="Submit a new payout"
          />
        )}
        <NavCard 
          title="Discover Servers" 
          link="/servers"
          description="Browse trading communities"
        />
        {!isMember && (
          <NavCard 
            title="Join a Server" 
            link="/servers"
            description="Join a trading community to submit payouts"
          />
        )}
      </div>
    </div>
  );
};

export default TraderDashboard;
