import DashboardHeader from '../../components/dashboard/DashboardHeader';
import WelcomeCard from '../../components/dashboard/WelcomeCard';
import FeatureCard from '../../components/dashboard/FeatureCard';
import NavCard from '../../components/dashboard/NavCard';
import './PlatformAdminDashboard.css';

const PlatformAdminDashboard = () => {
  return (
    <div className="dashboard-container">
      <DashboardHeader 
        title="Platform Owner Dashboard"
        subtitle="Complete system control"
      />
      <WelcomeCard 
        customGreeting="Welcome, Platform Owner!"
        showBadges={true} 
      />
      
      <div className="quick-access-section">
        <FeatureCard
          title="Platform Admin Control"
          description="Complete system control: Manage all users, servers, and payouts"
          link="/platform-admin"
          variant="admin"
        />
      </div>

      <div className="nav-grid">
        <NavCard 
          title="Platform Admin" 
          link="/platform-admin"
          description="Full system management"
        />
        <NavCard 
          title="Analytics" 
          link="/analytics"
          description="Platform-wide statistics"
        />
      </div>
    </div>
  );
};

export default PlatformAdminDashboard;
