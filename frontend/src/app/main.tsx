import React from 'react';
import ReactDOM from 'react-dom/client';

import { App } from './App';
import '../styles/globals.css';
import { registerServiceWorker } from '../shared/offline/registerServiceWorker';

void registerServiceWorker();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
