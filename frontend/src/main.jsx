import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { WalletProvider } from './contexts/WalletContext.jsx' // Import the provider

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* Wrap App with the WalletProvider */}
    <WalletProvider>
      <App />
    </WalletProvider>
  </React.StrictMode>,
)