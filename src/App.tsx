import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import './App.css';

// Component imports
import ImportData from './components/ImportData';
import BuildStrategy from './components/BuildStrategy';
import ViewResults from './components/ViewResults';

function Navigation() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Import Data' },
    { path: '/strategy', label: 'Build Strategy' },
    { path: '/results', label: 'View Results' },
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
          <Route path="/results" element={<ViewResults />} />
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