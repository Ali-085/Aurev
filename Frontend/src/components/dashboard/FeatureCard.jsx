import { useNavigate } from 'react-router-dom';
import './FeatureCard.css';

const FeatureCard = ({ title, description, link, variant = 'default' }) => {
  const navigate = useNavigate();

  return (
    <div 
      className={`feature-card feature-card-${variant}`} 
      onClick={() => navigate(link)}
    >
      <div className="feature-content">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <div className="feature-arrow">→</div>
    </div>
  );
};

export default FeatureCard;
