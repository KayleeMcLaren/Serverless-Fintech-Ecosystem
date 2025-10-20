import React, { useState, useEffect } from 'react';
import './App.css';

// --- PASTE YOUR API URL HERE ---
const API_URL = 'https://3p79xdboij.execute-api.us-east-1.amazonaws.com/v1';
const LOCAL_STORAGE_KEY = 'fintechWalletId';

function App() {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [walletIdInput, setWalletIdInput] = useState('');
  const [amountInput, setAmountInput] = useState(''); // State for credit/debit amount

  // Load wallet from localStorage on initial render
  useEffect(() => {
    const savedWalletId = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (savedWalletId) {
      console.log('Found saved wallet ID:', savedWalletId);
      setWalletIdInput(savedWalletId);
      handleFetchWallet(savedWalletId);
    }
  }, []);

  // Function to CREATE a new wallet
  const handleCreateWallet = async () => {
    // ... (keep this function exactly the same as before) ...
    setLoading(true);
    setError(null);
    setWallet(null);

    try {
      const response = await fetch(`${API_URL}/wallet`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setWallet(data.wallet);
      localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet.wallet_id); // Save ID
      setWalletIdInput(data.wallet.wallet_id); // Update input field
      console.log('Wallet created and ID saved:', data.wallet.wallet_id);
    } catch (e) {
      setError(`Failed to create wallet: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Function to FETCH an existing wallet
  const handleFetchWallet = async (idToFetch) => {
    // ... (keep this function exactly the same as before) ...
    const walletId = idToFetch || walletIdInput; // Use passed ID or input value
    if (!walletId) {
      setError('Please enter a Wallet ID to fetch.');
      return;
    }

    setLoading(true);
    setError(null);
    setWallet(null); // Clear previous wallet details

    try {
      const response = await fetch(`${API_URL}/wallet/${encodeURIComponent(walletId)}`); // Use GET and include ID in URL

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`Wallet not found.`);
        }
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setWallet(data); // The GET endpoint returns the wallet directly
      localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet_id); // Also save if fetched successfully
      setWalletIdInput(data.wallet_id); // Update input field
      console.log('Wallet fetched and ID saved:', data.wallet_id);
    } catch (e) {
      setError(`Failed to fetch wallet: ${e.message}`);
      setWallet(null); // Ensure no stale wallet data is shown on error
    } finally {
      setLoading(false);
    }
  };

  // --- NEW: Function to handle Credit/Debit API calls ---
  const handleTransaction = async (type) => { // type will be 'credit' or 'debit'
    if (!wallet || !wallet.wallet_id) {
      setError('No wallet loaded to perform transaction.');
      return;
    }
    if (!amountInput || parseFloat(amountInput) <= 0) {
      setError('Please enter a positive amount.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_URL}/wallet/${encodeURIComponent(wallet.wallet_id)}/${type}`, // Use 'credit' or 'debit' path
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ amount: amountInput }), // Send amount in body
        }
      );

      const responseBody = await response.json(); // Read body even for errors

      if (!response.ok) {
        // Try to get error message from API response, fallback to status text
        const apiErrorMsg = responseBody?.message || response.statusText;
        throw new Error(`HTTP error! Status: ${response.status} - ${apiErrorMsg}`);
      }

      // Update the wallet state with the new balance from the response
      setWallet((prevWallet) => ({
        ...prevWallet,
        balance: responseBody.balance, // API returns the updated balance
      }));
      setAmountInput(''); // Clear the amount input on success
      console.log(`Transaction ${type} successful. New balance:`, responseBody.balance);

    } catch (e) {
      setError(`Failed to ${type} wallet: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="App">
      <header className="App-header">
        <h1>Serverless Fintech Ecosystem</h1>
      </header>

      <div className="card">
        <h2>Digital Wallet</h2>

        {/* --- Input and Fetch Button --- */}
        <div className="input-group">
          <input
            type="text"
            value={walletIdInput}
            onChange={(e) => setWalletIdInput(e.target.value)}
            placeholder="Enter Wallet ID"
            disabled={loading}
          />
          <button onClick={() => handleFetchWallet()} disabled={loading || !walletIdInput}>
            {loading ? 'Fetching...' : 'Fetch Wallet'}
          </button>
        </div>

        <p>Or</p>

        {/* --- Create Button --- */}
        <button onClick={handleCreateWallet} disabled={loading}>
          {loading ? 'Creating...' : 'Create New Wallet'}
        </button>

        {/* --- Loading and Error Display --- */}
        {loading && <p>Loading...</p>}
        {error && <p className="error">{error}</p>}

        {/* --- Wallet Details and Transaction Section --- */}
        {wallet && (
          <div className="wallet-details">
            <h3>Wallet Details</h3>
            <p>
              <strong>Wallet ID:</strong> <span>{wallet.wallet_id}</span>
            </p>
            <p>
              <strong>Balance:</strong> <span>${wallet.balance}</span>
            </p>
            <p>
              <strong>Currency:</strong> <span>{wallet.currency}</span>
            </p>

            {/* --- NEW: Credit/Debit Input and Buttons --- */}
            {/* --- NEW: Credit/Debit Input and Buttons --- */}
          <div className="transaction-section">
            <h4>Make a Transaction</h4>
            {/* Input is now separate from buttons */}
            <div className="input-group amount-input-group"> {/* Added class */}
              <input
                type="number"
                value={amountInput}
                onChange={(e) => setAmountInput(e.target.value)}
                placeholder="Enter amount"
                disabled={loading}
                min="0.01"
                step="0.01"
              />
            </div>
            {/* New div to wrap and center buttons */}
            <div className="button-group"> {/* New wrapper div */}
              <button
                onClick={() => handleTransaction('credit')}
                disabled={loading || !amountInput}
                className="credit-button"
              >
                Credit (Deposit)
              </button>
              <button
                onClick={() => handleTransaction('debit')}
                disabled={loading || !amountInput}
                className="debit-button"
              >
                Debit (Withdraw)
              </button>
            </div>
          </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;