import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App.jsx';
import { SecurityProvider } from './context/SecurityContext.jsx';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
        <SecurityProvider>
            <App />
        </SecurityProvider>
    </React.StrictMode>
);
