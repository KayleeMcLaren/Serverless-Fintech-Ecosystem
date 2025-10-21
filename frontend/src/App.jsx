import React, { useState, useEffect } from 'react';
import SavingsGoals from './SavingsGoals'; 
import MicroLoans from './MicroLoans';
import PaymentSimulator from './PaymentSimulator';

// --- PASTE YOUR API URL HERE ---
const API_URL = 'https://3p79xdboij.execute-api.us-east-1.amazonaws.com/v1';
const LOCAL_STORAGE_KEY = 'fintechWalletId';

function App() {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [walletIdInput, setWalletIdInput] = useState('');
  const [amountInput, setAmountInput] = useState('');

  // --- Keep useEffect, handleCreateWallet, handleFetchWallet, handleTransaction ---
  // --- No changes needed in the JavaScript logic itself ---

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
    setLoading(true);
    setError(null);
    setWallet(null);
    try {
      const response = await fetch(`${API_URL}/wallet`, { method: 'POST' });
      if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
      const data = await response.json();
      setWallet(data.wallet);
      localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet.wallet_id);
      setWalletIdInput(data.wallet.wallet_id);
      console.log('Wallet created and ID saved:', data.wallet.wallet_id);
    } catch (e) {
      setError(`Failed to create wallet: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Function to FETCH an existing wallet
  const handleFetchWallet = async (idToFetch) => {
    const walletId = idToFetch || walletIdInput;
    if (!walletId) {
      setError('Please enter a Wallet ID to fetch.');
      return;
    }
    setLoading(true);
    setError(null);
    setWallet(null);
    try {
      const response = await fetch(`${API_URL}/wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
        if (response.status === 404) throw new Error(`Wallet not found.`);
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setWallet(data);
      localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet_id);
      setWalletIdInput(data.wallet_id);
      console.log('Wallet fetched and ID saved:', data.wallet_id);
    } catch (e) {
      setError(`Failed to fetch wallet: ${e.message}`);
      setWallet(null);
    } finally {
      setLoading(false);
    }
  };

  // Function to handle Credit/Debit API calls
  const handleTransaction = async (type) => {
    if (!wallet || !wallet.wallet_id) {
      setError('No wallet loaded to perform transaction.');
      return;
    }
    // Ensure amountInput is treated as a string for validation, then parse
    const amountStr = String(amountInput).trim();
    if (!amountStr || parseFloat(amountStr) <= 0) {
      setError('Please enter a positive amount.');
      return;
    }
    const amount = parseFloat(amountStr); // Use the parsed float

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_URL}/wallet/${encodeURIComponent(wallet.wallet_id)}/${type}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          // Send amount as a string, matching backend expectation
          body: JSON.stringify({ amount: amount.toFixed(2) }),
        }
      );
      const responseBody = await response.json();
      if (!response.ok) {
        const apiErrorMsg = responseBody?.message || response.statusText;
        throw new Error(`HTTP error! Status: ${response.status} - ${apiErrorMsg}`);
      }
      // Update balance using the string value returned by API
      setWallet((prevWallet) => ({ ...prevWallet, balance: responseBody.balance }));
      setAmountInput('');
      console.log(`Transaction ${type} successful. New balance:`, responseBody.balance);
    } catch (e) {
      setError(`Failed to ${type} wallet: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };


  // --- JSX with Tailwind Classes ---
  return (
    // App container: Centered, max-width, padding, background, shadow, etc.
    <div className="max-w-xl mx-auto my-8 p-8 bg-white rounded-lg shadow-md text-gray-800"> {/* Added text color */}
      {/* Header section */}
      <header className="text-center mb-6">
        <h1 className="text-3xl font-bold text-gray-700">Serverless Fintech Ecosystem</h1>
      </header>

      {/* Card for Wallet */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8 shadow-sm">
        <h2 className="text-xl font-semibold text-gray-700 mb-6 text-center">Digital Wallet</h2>

        {/* Input group for fetching wallet */}
        <div className="flex flex-wrap gap-3 mb-4 items-stretch"> {/* Use items-stretch */}
          <input
            type="text"
            value={walletIdInput}
            onChange={(e) => setWalletIdInput(e.target.value)}
            placeholder="Enter Wallet ID"
            disabled={loading}
            // Tailwind classes for input styling
            className="flex-grow basis-60 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 min-w-[150px]" // Added min-width
          />
          <button
            onClick={() => handleFetchWallet()}
            disabled={loading || !walletIdInput}
            // Tailwind classes for button styling
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-blue-300 disabled:cursor-not-allowed flex-shrink-0"
          >
            {loading ? 'Fetching...' : 'Fetch Wallet'}
          </button>
        </div>

        <p className="text-center text-gray-500 my-4">Or</p>

        {/* Create Button */}
        <div className="text-center">
          <button
            onClick={handleCreateWallet}
            disabled={loading}
             // Tailwind classes for button styling
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating...' : 'Create New Wallet'}
          </button>
        </div>

        {/* Loading and Error Display */}
        {loading && <p className="text-center text-blue-600 mt-4">Loading...</p>}
        {error && (
          // Tailwind classes for error styling
          <p className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm text-left"> {/* Added text-left */}
            {error}
          </p>
        )}

        {/* Wallet Details and Transaction Section */}
        {wallet && (
          // Tailwind classes for wallet details box
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-md text-left">
            <h3 className="text-lg font-semibold text-blue-700 mb-3">Wallet Details</h3>
            <p className="text-sm mb-1 break-words"> {/* break-words for long IDs */}
              <strong className="text-gray-600">Wallet ID:</strong>
              <span className="ml-2 font-mono text-blue-600">{wallet.wallet_id}</span>
            </p>
            <p className="text-sm mb-1">
              <strong className="text-gray-600">Balance:</strong>
              <span className="ml-2 font-mono text-blue-600">${wallet.balance}</span>
            </p>
            <p className="text-sm">
              <strong className="text-gray-600">Currency:</strong>
              <span className="ml-2 font-mono text-blue-600">{wallet.currency}</span>
            </p>

            {/* Transaction Section */}
            <div className="mt-5 pt-4 border-t border-blue-200">
              <h4 className="text-md font-semibold text-gray-700 mb-3">Make a Transaction</h4>
              {/* Amount Input */}
              <div className="mb-3"> {/* Removed input-group class */}
                <input
                  type="number"
                  value={amountInput}
                  onChange={(e) => setAmountInput(e.target.value)}
                  placeholder="Enter amount"
                  disabled={loading}
                  min="0.01"
                  step="0.01"
                   // Tailwind classes for input styling - now takes full width
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                />
              </div>
              {/* Button Group */}
              <div className="flex justify-center gap-3 mt-2"> {/* Use flexbox to center and space buttons */}
                <button
                  onClick={() => handleTransaction('credit')}
                  disabled={loading || !amountInput}
                   // Tailwind classes for CREDIT button
                  className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:bg-green-300 disabled:cursor-not-allowed"
                >
                  Credit (Deposit)
                </button>
                <button
                  onClick={() => handleTransaction('debit')}
                  disabled={loading || !amountInput}
                   // Tailwind classes for DEBIT button
                  className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:bg-red-300 disabled:cursor-not-allowed"
                >
                  Debit (Withdraw)
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
      {/* It only renders fully if a wallet is loaded */}
    <SavingsGoals walletId={wallet ? wallet.wallet_id : null} apiUrl={API_URL} />
    <MicroLoans walletId={wallet ? wallet.wallet_id : null} apiUrl={API_URL} />
    <PaymentSimulator walletId={wallet ? wallet.wallet_id : null} apiUrl={API_URL} />
    </div>
  );
}

export default App;