/**
 * Application Entry Point
 * 
 * SECURITY:
 * - StrictMode enabled for development warnings
 * - Root component mounting
 */
// src/main.jsx (or main.tsx)
import axios from 'axios';

// Intercept all outgoing Axios requests
axios.interceptors.request.use(
  (config) => {
    return config; // return config so request proceeds
  },
  (error) => {
    return Promise.reject(error);
  }
);

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
