import DashboardHeader from '../../components/dashboard/DashboardHeader';
import WelcomeCard from '../../components/dashboard/WelcomeCard';
import FeatureCard from '../../components/dashboard/FeatureCard';
import './ModeratorDashboard.css';

const ModeratorDashboard = () => {
  return (
    <div className="dashboard-container">
      <DashboardHeader 
        title="Moderator Dashboard"
        subtitle="Review and manage platform content"
      />
      <WelcomeCard showBadges={true} />
      
      <div className="quick-access-section">
        <FeatureCard
          title="Moderation Panel"
          description="Review payout submissions and manage content"
          link="/moderator"
          variant="moderator"
        />
      </div>
    </div>
  );
};

export default ModeratorDashboard;
