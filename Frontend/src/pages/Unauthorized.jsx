/**
 * Unauthorized Access Page
 * 
 * Shown when user tries to access a route they don't have permission for
 */

import { Link } from 'react-router-dom';
import './Unauthorized.css';

const Unauthorized = () => {
  return (
    <div className="unauthorized-page">
      <h1>403 - Unauthorized</h1>
      <p>You don't have permission to access this page.</p>
      <Link to="/dashboard">Go to Dashboard</Link>
    </div>
  );
};

export default Unauthorized;
