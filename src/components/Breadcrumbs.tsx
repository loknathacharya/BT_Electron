import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import './Breadcrumbs.css';

interface BreadcrumbItem {
  label: string;
  path?: string;
  icon?: string;
}

interface BreadcrumbsProps {
  items?: BreadcrumbItem[];
}

const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ items }) => {
  const location = useLocation();
  const navigate = useNavigate();

  // Map of routes to breadcrumb labels
  const routeLabels: { [key: string]: string } = {
    '/': '� Data Management',
    '/scanner': '🔍 Scanner',
    '/data-management': '📊 Data Management',
    '/import': '📥 Import Data',
    '/backtest': '📈 Backtest',
    '/portfolio': '💼 Portfolio',
    '/walk-forward': '🔄 Walk-Forward',
    '/backup-recovery': '💾 Backup & Recovery',
  };

  // Generate breadcrumbs from current route
  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    if (items) {
      return items;
    }

    const path = location.pathname;
    const label = routeLabels[path] || path;

    return [{ label, icon: undefined }];
  };

  const breadcrumbs = generateBreadcrumbs();

  const handleNavigate = (path: string | undefined) => {
    if (path) {
      navigate(path);
    }
  };

  return (
    <div className="breadcrumbs">
      <button
        className="breadcrumb-home"
        onClick={() => navigate('/')}
        title="Back to Home"
      >
        🏠 Home
      </button>

      {breadcrumbs.map((item, idx) => (
        <div key={idx} className="breadcrumb-item">
          <span className="breadcrumb-separator">›</span>
          {item.path ? (
            <button
              className="breadcrumb-link"
              onClick={() => handleNavigate(item.path)}
              title={`Go to ${item.label}`}
            >
              {item.label}
            </button>
          ) : (
            <span className="breadcrumb-current">{item.label}</span>
          )}
        </div>
      ))}
    </div>
  );
};

export default Breadcrumbs;
