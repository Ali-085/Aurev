import { useNavigate } from 'react-router-dom';
import './NavCard.css';

const NavCard = ({ title, icon, link, description }) => {
  const navigate = useNavigate();

  return (
    <div className="nav-card" onClick={() => navigate(link)}>
      {icon && <div className="nav-card-icon">{icon}</div>}
      <h3>{title}</h3>
      {description && <p className="nav-card-description">{description}</p>}
    </div>
  );
};

export default NavCard;
