import { HashRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import './App.css';

// Component imports
import ImportData from './components/ImportData';
import ViewResults from './components/ViewResults';
import Scanner from '@/components/Scanner';
import BacktestEngine from './components/BacktestEngine';
import PortfolioBacktest from './components/PortfolioBacktest';
import { WalkForwardAnalysis } from './components/WalkForwardAnalysis';
import BackupRecovery from './components/BackupRecovery';
import Breadcrumbs from './components/Breadcrumbs';

function Navigation() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Data Management' },
    { path: '/scanner', label: 'Scanner' },
    { path: '/backtest', label: 'Backtest' },
    { path: '/portfolio', label: 'Portfolio' },
    { path: '/walk-forward', label: 'Walk-Forward' },
    { path: '/backup-recovery', label: 'Backup & Recovery' },
  ];

  return (
    <nav className="navigation">
      <div className="nav-brand">
        <h1>BYOD Strategy Backtesting</h1>
      </div>
      <ul className="nav-links">
        {navItems.map((item) => (
          <li key={item.path}>
            <Link
              to={item.path}
              className={location.pathname === item.path ? 'active' : ''}
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function AppContent() {
  return (
    <div className="app">
      <Navigation />
      <Breadcrumbs />
      <main className="main-content">
        <Routes>
            {/* Data Management as home page */}
            <Route path="/" element={<ViewResults />} />
            {/* Keep a route for the legacy /data-management path to avoid breaking internal links */}
            <Route path="/data-management" element={<ViewResults />} />
            {/* Import Data modal route — ViewResults handles showing modal based on location.pathname */}
            <Route path="/import" element={<ViewResults />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/backtest" element={<BacktestEngine />} />
          <Route path="/portfolio" element={<PortfolioBacktest scannerSpec={{}} />} />
          <Route path="/walk-forward" element={<WalkForwardAnalysis scannerSpec={{}} />} />
          <Route path="/backup-recovery" element={<BackupRecovery />} />
          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  console.log('App component rendering...');
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;