import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import './App.css';

// Component imports
import ImportData from './components/ImportData';
import BuildStrategy from './components/BuildStrategy';
import ViewResults from './components/ViewResults';
import BacktestDev from './components/BacktestDev';
import Scanner from '@/components/Scanner';
import BacktestBuilder from './components/BacktestBuilder';

function Navigation() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Import Data' },
    { path: '/strategy', label: 'Build Strategy' },
    { path: '/scanner', label: 'Scanner' },
    { path: '/data-management', label: 'Data Management' },
    { path: '/results', label: 'Results & Analysis' },
    { path: '/backtest', label: 'Backtest' },
    { path: '/backtest-dev', label: 'Backtest Dev' },
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
          <Route path="/" element={<ImportData />} />
          <Route path="/strategy" element={<BuildStrategy />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/data-management" element={<ViewResults />} />
          <Route path="/results" element={<ViewResults />} />
          <Route path="/backtest" element={<BacktestBuilder />} />
          <Route path="/backtest-dev" element={<BacktestDev />} />
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