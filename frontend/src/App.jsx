import React, { useState } from 'react';
import './App.css';

// --- PASTE YOUR API URL HERE ---
// This is the 'v1' stage URL from your terraform apply output
const API_URL = 'https://3p79xdboij.execute-api.us-east-1.amazonaws.com/v1';

function App() {
  // useState hooks to store our component's data
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // This function is called when the button is clicked
  const handleCreateWallet = async () => {
    setLoading(true);
    setError(null);
    setWallet(null);

    try {
      // Use the browser's 'fetch' API to call our backend
      const response = await fetch(`${API_URL}/wallet`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      // Save the new wallet data in our component's state
      setWallet(data.wallet);
    } catch (e) {
      setError(`Failed to create wallet: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Serverless Fintech Ecosystem</h1>

        <div className="card">
          <h2>Digital Wallet</h2>

          {/* Show the button only if we don't have a wallet */}
          {!wallet && (
            <button onClick={handleCreateWallet} disabled={loading}>
              {loading ? 'Creating...' : 'Create New Wallet'}
            </button>
          )}

          {/* Show loading, error, or wallet details */}
          {loading && <p>Loading...</p>}
          {error && <p className="error">{error}</p>}

          {/* Once the wallet is created, display its details */}
          {wallet && (
            <div className="wallet-details">
              <h3>Wallet Created Successfully!</h3>
              <p>
                <strong>Wallet ID:</strong> <span>{wallet.wallet_id}</span>
              </p>
              <p>
                <strong>Balance:</strong> <span>${wallet.balance}</span>
              </p>
              <p>
                <strong>Currency:</strong> <span>{wallet.currency}</span>
              </p>
            </div>
          )}
        </div>

      </header>
    </div>
  );
}

export default App;