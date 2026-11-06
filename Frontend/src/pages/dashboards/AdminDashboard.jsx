import DashboardHeader from '../../components/dashboard/DashboardHeader';
import WelcomeCard from '../../components/dashboard/WelcomeCard';
import FeatureCard from '../../components/dashboard/FeatureCard';
import './AdminDashboard.css';

const AdminDashboard = () => {
  return (
    <div className="dashboard-container">
      <DashboardHeader 
        title="Admin Dashboard"
        subtitle="Manage platform operations"
      />
      <WelcomeCard showBadges={true} />
      
      <div className="quick-access-section">
        <FeatureCard
          title="Admin Control Panel"
          description="Manage server settings, members, and payout reviews"
          link="/admin"
          variant="admin"
        />
      </div>
    </div>
  );
};

export default AdminDashboard;
