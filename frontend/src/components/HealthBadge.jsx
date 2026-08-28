import React, { useState, useEffect } from 'react';
import { checkHealth } from '../services/api';

export const HealthBadge = () => {
  const [status, setStatus] = useState('checking');
  const [lastChecked, setLastChecked] = useState(null);

  const fetchHealth = async () => {
    try {
      const data = await checkHealth();
      if (data && data.status === 'ok') {
        setStatus('healthy');
      } else {
        setStatus('unhealthy');
      }
    } catch (err) {
      setStatus('unhealthy');
    } finally {
      setLastChecked(new Date().toLocaleTimeString());
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className={`health-badge ${status}`}
      title={lastChecked ? `Backend Status: ${status} (Checked: ${lastChecked})` : 'Checking backend status...'}
      id="backend-health-indicator"
    >
      <span className="pulse-dot" />
      <span>Backend: {status === 'healthy' ? 'Online (ok)' : status === 'checking' ? 'Connecting...' : 'Offline'}</span>
    </div>
  );
};

export default HealthBadge;
