import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { canAdmin, canModerate } from '../../utils/permissions';
import DashboardHeader from '../../components/dashboard/DashboardHeader';
import WelcomeCard from '../../components/dashboard/WelcomeCard';
import FeatureCard from '../../components/dashboard/FeatureCard';
import NavCard from '../../components/dashboard/NavCard';
import './ServerOwnerDashboard.css';

const ServerOwnerDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Redirect users with elevated roles to their appropriate dashboards
  useEffect(() => {
    if (!user) return;
    
    if (canAdmin(user)) {
      navigate('/dashboard/admin', { replace: true });
    } else if (canModerate(user)) {
      navigate('/dashboard/moderator', { replace: true });
    }
  }, [user, navigate]);

  return (
    <div className="dashboard-container">
      <DashboardHeader 
        title="Server Owner Dashboard"
        subtitle="Manage your servers and analytics"
      />
      <WelcomeCard />
      <div className="nav-grid">
        <NavCard 
          title="Server Analytics" 
          link="/my-servers"
          description="View detailed server metrics"
        />
        <NavCard 
          title="Server Settings" 
          link="/my-servers"
          description="Manage server logo and description"
        />
        <NavCard 
          title="Submit Payout" 
          link="/payouts"
          description="Submit a new payout"
        />
      </div>
    </div>
  );
};

export default ServerOwnerDashboard;
