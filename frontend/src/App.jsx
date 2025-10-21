import React, { useState, useEffect } from 'react';
// Import the components
import SavingsGoals from './SavingsGoals';
import MicroLoans from './MicroLoans';
import PaymentSimulator from './PaymentSimulator';
import DebtOptimiser from './DebtOptimiser';
import {
  WalletIcon,
  BanknotesIcon, // Using this for Savings
  CreditCardIcon, // Using this for Loans (or CurrencyDollarIcon)
  ArrowsRightLeftIcon, // Using this for Payments/Transactions
  ScaleIcon // Using this for Debt/Optimiser
} from '@heroicons/react/24/outline'; // Use outline style

// --- PASTE YOUR API URL HERE ---
const API_URL = 'https://3p79xdboij.execute-api.us-east-1.amazonaws.com/v1';
const LOCAL_STORAGE_KEY = 'fintechWalletId';

function App() {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(false); // General loading state
  const [error, setError] = useState(null); // General error state
  const [walletIdInput, setWalletIdInput] = useState('');
  const [amountInput, setAmountInput] = useState('');
  const [activeTab, setActiveTab] = useState('wallet'); // Default to wallet tab

  // --- Wallet Action Functions (Keep these as they are) ---
  // Load wallet from localStorage on initial render
  useEffect(() => {
    const savedWalletId = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (savedWalletId) {
      console.log('Found saved wallet ID:', savedWalletId);
      setWalletIdInput(savedWalletId);
      handleFetchWallet(savedWalletId); // Fetch wallet on load
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    setWallet(null); // Clear previous wallet first
    try {
      const response = await fetch(`${API_URL}/wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
        if (response.status === 404) throw new Error(`Wallet not found.`);
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setWallet(data); // Fetched wallet data
      localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet_id);
      setWalletIdInput(data.wallet_id);
      console.log('Wallet fetched and ID saved:', data.wallet_id);
    } catch (e) {
      setError(`Failed to fetch wallet: ${e.message}`);
      setWallet(null); // Ensure null on error
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
    const amountStr = String(amountInput).trim();
    if (!amountStr || parseFloat(amountStr) <= 0) {
      setError('Please enter a positive amount.');
      return;
    }
    const amount = parseFloat(amountStr);
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_URL}/wallet/${encodeURIComponent(wallet.wallet_id)}/${type}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: amount.toFixed(2) }),
        }
      );
      const responseBody = await response.json();
      if (!response.ok) {
        const apiErrorMsg = responseBody?.message || response.statusText;
        throw new Error(`HTTP error! Status: ${response.status} - ${apiErrorMsg}`);
      }
      setWallet((prevWallet) => ({ ...prevWallet, balance: responseBody.balance }));
      setAmountInput('');
      console.log(`Transaction ${type} successful. New balance:`, responseBody.balance);
    } catch (e) {
      setError(`Failed to ${type} wallet: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };
  // --- End Wallet Action Functions ---


  // --- Function to render content based on active tab ---
  const renderTabContent = () => {
    switch (activeTab) {
      case 'wallet':
        return (
          // Use neutral background and border
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mb-8 shadow-sm">
            <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Digital Wallet</h2>
             {/* Input group for fetching wallet */}
            <div className="flex flex-wrap gap-3 mb-4 items-stretch">
            <input
                type="text"
                value={walletIdInput}
                onChange={(e) => setWalletIdInput(e.target.value)}
                placeholder="Enter Wallet ID"
                disabled={loading}
                // Use neutral border, focus ring with primary blue
                className="flex-grow basis-60 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
            />
            <button
                onClick={() => handleFetchWallet()}
                disabled={loading || !walletIdInput}
                // Use primary blue button styles
                className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed flex-shrink-0"
            >
                {loading && !wallet ? 'Fetching...' : 'Fetch Wallet'}
            </button>
            </div>
             <p className="text-center text-neutral-500 my-4">Or</p>
             {/* Create Button */}
            <div className="text-center">
            <button
                onClick={handleCreateWallet}
                disabled={loading}
                 // Use primary blue button styles
                className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed"
            >
                 {loading && !wallet ? 'Creating...' : 'Create New Wallet'}
            </button>
            </div>

            {/* Wallet Details and Transactions - Only if wallet exists */}
            {wallet && (
                 // Use lighter primary blue background with opacity, border with opacity
                 <div className="mt-6 p-4 bg-primary-blue-light/20 border border-primary-blue/30 rounded-md text-left">
                    <h3 className="text-lg font-semibold text-primary-blue-dark mb-3">Wallet Details</h3>
                    <p className="text-sm mb-1 break-words">
                        <strong className="text-neutral-600">Wallet ID:</strong>
                        <span className="ml-2 font-mono text-primary-blue-dark">{wallet.wallet_id}</span>
                    </p>
                    <p className="text-sm mb-1">
                        <strong className="text-neutral-600">Balance:</strong>
                        <span className="ml-2 font-mono text-primary-blue-dark">${wallet.balance}</span>
                    </p>
                    <p className="text-sm">
                        <strong className="text-neutral-600">Currency:</strong>
                        <span className="ml-2 font-mono text-primary-blue-dark">{wallet.currency}</span>
                    </p>
                     {/* Transaction Section */}
                    <div className="mt-5 pt-4 border-t border-primary-blue/30"> {/* Border with opacity */}
                        <h4 className="text-md font-semibold text-neutral-700 mb-3">Make a Transaction</h4>
                        <div className="mb-3">
                            <input
                            type="number"
                            value={amountInput}
                            onChange={(e) => setAmountInput(e.target.value)}
                            placeholder="Enter amount"
                            disabled={loading}
                            min="0.01" step="0.01"
                            // Use neutral border, focus ring with primary blue
                            className="w-full p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
                            />
                        </div>
                        <div className="flex justify-center gap-3 mt-2">
                            <button
                                onClick={() => handleTransaction('credit')}
                                disabled={loading || !amountInput}
                                // Use accent green button styles
                                className="px-4 py-2 bg-accent-green text-white rounded-md hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-2 disabled:bg-accent-green-light disabled:cursor-not-allowed"
                            >
                                Credit
                            </button>
                            <button
                                onClick={() => handleTransaction('debit')}
                                disabled={loading || !amountInput}
                                // Use accent red button styles
                                className="px-4 py-2 bg-accent-red text-white rounded-md hover:bg-accent-red-dark focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 disabled:bg-accent-red-light disabled:cursor-not-allowed"
                            >
                                Debit
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Display loading specific to wallet actions */}
            {loading && activeTab === 'wallet' && <p className="text-center text-primary-blue mt-4">Processing Wallet Action...</p>}
            {/* Error display moved outside this component, handled globally */}
          </div>
        );

      case 'savings':
        return <SavingsGoals walletId={wallet ? wallet.wallet_id : null} apiUrl={API_URL} />;
      case 'loans':
        return <MicroLoans walletId={wallet ? wallet.wallet_id : null} apiUrl={API_URL} />;
      case 'payments':
        return <PaymentSimulator walletId={wallet ? wallet.wallet_id : null} apiUrl={API_URL} />;
      case 'optimiser':
        return <DebtOptimiser walletId={wallet ? wallet.wallet_id : null} apiUrl={API_URL} />;
      default:
        return null;
    }
  };

  // --- Main JSX Structure ---
  return (
    // Use neutral text color from body (defined in index.css)
    <div className="max-w-3xl mx-auto my-8 p-8 bg-white rounded-lg shadow-md text-neutral-800">
      <header className="text-center mb-6">
      <h1 className="text-3xl font-bold text-neutral-800">Serverless Fintech Ecosystem</h1>
      </header>

      {/* Tab Navigation */}
      <nav className="flex justify-center border-b border-neutral-300 mb-8 space-x-1 sm:space-x-2">
      {[
        { id: 'wallet', label: 'Wallet', Icon: WalletIcon },
        { id: 'savings', label: 'Savings', Icon: BanknotesIcon },
        { id: 'loans', label: 'Loans', Icon: CreditCardIcon },
        { id: 'payments', label: 'Payments', Icon: ArrowsRightLeftIcon },
        { id: 'optimiser', label: 'Debt Plan', Icon: ScaleIcon },
      ].map((tab) => (
        <button
        key={tab.id}
        onClick={() => { setActiveTab(tab.id); setError(null); }}
        className={`flex items-center gap-1 sm:gap-1.5 py-2 px-2 sm:px-3 text-xs sm:text-sm font-medium capitalize focus:outline-none whitespace-nowrap ${
          activeTab === tab.id
          ? 'border-b-2 border-primary-blue text-primary-blue'
          : 'text-neutral-500 hover:text-neutral-700 hover:border-neutral-300 border-b-2 border-transparent'
        }`}
        >
        <tab.Icon className="h-4 w-4 sm:h-5 sm:w-5" />
        {tab.label}
        </button>
      ))}
      </nav>

      {/* Main Content Area */}
      <main>
        {/* General Error Display - Use accent red */}
        {error && <p className="mb-4 p-3 bg-accent-red-light border border-accent-red text-accent-red-dark rounded-md text-sm text-left">{error}</p>}

        {/* Render the content for the active tab */}
        {renderTabContent()}
      </main>
    </div>
  );
}

export default App;