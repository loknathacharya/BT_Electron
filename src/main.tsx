import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './App.css'

console.log('main.tsx loaded');
console.log('Root element:', document.getElementById('root'));

const rootElement = document.getElementById('root');
if (rootElement) {
  console.log('Creating React root...');
  const root = ReactDOM.createRoot(rootElement);
  console.log('Rendering React app...');
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
  console.log('React app rendered successfully');
} else {
  console.error('Root element not found!');
}