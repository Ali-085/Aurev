import './DashboardHeader.css';

const DashboardHeader = ({ title, subtitle }) => {

  return (
    <div className="dashboard-header">
      <div>
        <h1 className="dashboard-title">{title || 'Aurevia'}</h1>
        <p className="dashboard-subtitle">{subtitle || 'Trading Leaderboard Platform'}</p>
      </div>
    </div>
  );
};

export default DashboardHeader;
