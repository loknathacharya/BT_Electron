import { HashRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import './App.css';

// Component imports
import ImportData from './components/ImportData';
import ViewResults from './components/ViewResults';
import BacktestDev from './components/BacktestDev';
import Scanner from '@/components/Scanner';
import BacktestBuilder from './components/BacktestBuilder';
import PortfolioBacktest from './components/PortfolioBacktest';
import { WalkForwardAnalysis } from './components/WalkForwardAnalysis';
import BackupRecovery from './components/BackupRecovery';

function Navigation() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Import Data' },
    { path: '/scanner', label: 'Scanner' },
    { path: '/data-management', label: 'Data Management' },
    { path: '/backtest', label: 'Backtest' },
    { path: '/backtest-dev', label: 'Backtest Dev' },
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
      <main className="main-content">
        <Routes>
          {/* Import Data as home page */}
          <Route path="/" element={<ImportData />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/data-management" element={<ViewResults />} />
          <Route path="/backtest" element={<BacktestBuilder />} />
          <Route path="/backtest-dev" element={<BacktestDev />} />
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