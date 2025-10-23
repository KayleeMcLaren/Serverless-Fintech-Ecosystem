import React, { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
// Import the components
import SavingsGoals from './SavingsGoals';
import MicroLoans from './MicroLoans';
import PaymentSimulator from './PaymentSimulator';
import DebtOptimiser from './DebtOptimiser';
import {
  WalletIcon,
  BanknotesIcon,
  CreditCardIcon,
  ArrowsRightLeftIcon,
  ScaleIcon
} from '@heroicons/react/24/outline';
import TransactionHistory from './TransactionHistory';

// --- PASTE YOUR API URL HERE ---
const API_URL = 'https://3p79xdboij.execute-api.us-east-1.amazonaws.com/v1';
const LOCAL_STORAGE_KEY = 'fintechWalletId';

// --- formatCurrency Helper ---
const formatCurrency = (amount) => {
    try {
      const numberAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
      if (isNaN(numberAmount)) return String(amount);
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numberAmount);
    } catch (e) {
      console.error("Error formatting currency:", amount, e);
      return String(amount); // Fallback
    }
};
// --- End formatCurrency ---

function App() {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [walletIdInput, setWalletIdInput] = useState('');
  const [amountInput, setAmountInput] = useState('');
  const [activeTab, setActiveTab] = useState('wallet');
  const [transactionCount, setTransactionCount] = useState(0);

  // Load wallet from localStorage on initial render
  useEffect(() => {
    const savedWalletId = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (savedWalletId) {
      console.log('Found saved wallet ID:', savedWalletId);
      setWalletIdInput(savedWalletId);
      handleFetchWallet(savedWalletId, true); // Pass true to indicate initial load
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Function to CREATE a new wallet (with toast) ---
  const handleCreateWallet = async () => {
    setLoading(true);
    setError(null);
    setWallet(null);
    await toast.promise(
      fetch(`${API_URL}/wallet`, { method: 'POST' })
        .then(async (response) => {
          if (!response.ok) {
            let errorMsg = `HTTP error! Status: ${response.status}`;
            try { const errData = await response.json(); errorMsg = errData.message || errorMsg; } catch (e) {}
            throw new Error(errorMsg);
          }
          return response.json();
        })
        .then((data) => {
          setWallet(data.wallet);
          localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet.wallet_id);
          setWalletIdInput(data.wallet.wallet_id);
          setTransactionCount(prev => prev + 1);
          console.log('Wallet created and ID saved:', data.wallet.wallet_id);
        }),
      {
        loading: 'Creating wallet...',
        success: <b>Wallet created!</b>,
        error: (err) => <b>Failed to create wallet: {err.message}</b>,
      }
    );
    setLoading(false);
  };

  // --- Function to FETCH an existing wallet (SILENT - NO TOAST) ---
  const handleFetchWallet = async (idToFetch, isInitialLoad = false) => {
    const walletId = idToFetch || walletIdInput;
    if (!walletId) {
      toast.error('Please enter a Wallet ID.'); // Still toast for validation
      return;
    }
    setLoading(true);
    setError(null);
    if (!isInitialLoad) {
        setWallet(null);
    }
    
    try {
        console.log(`Fetching wallet: ${walletId}`);
        const response = await fetch(`${API_URL}/wallet/${encodeURIComponent(walletId)}`);
        if (!response.ok) {
           let errorMsg = `HTTP error! Status: ${response.status}`;
           if (response.status === 404) errorMsg = `Wallet ${walletId} not found.`;
           else { try { const errData = await response.json(); errorMsg = errData.message || errorMsg; } catch(e){} }
           throw new Error(errorMsg);
        }
        const data = await response.json();
        setWallet(data);
        if (idToFetch || !wallet) {
           localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet_id);
           setWalletIdInput(data.wallet_id);
        }
        console.log('Wallet fetched:', data.wallet_id);
        setTransactionCount(prev => prev + 1); // Refresh history on fetch
        return data; // Return data for the toast promise (if wrapped)
    } catch (e) {
        setError(`Failed to fetch wallet: ${e.message}`); // Set inline error
        setWallet(null);
        throw e; // Re-throw for the toast promise to catch
    } finally {
        setLoading(false);
    }
  };

  // --- Function to refresh wallet balance AND trigger history refresh ---
  const refreshWalletAndHistory = () => {
      console.log("Refreshing wallet balance and transaction history...");
      if (wallet?.wallet_id) {
          // Call the silent fetch function
          handleFetchWallet(wallet.wallet_id, true);
          setTransactionCount(prev => prev + 1);
      }
  };

  // --- Function to handle Credit/Debit API calls (with toast) ---
  const handleTransaction = async (type) => {
    if (!wallet || !wallet.wallet_id) {
      toast.error('No wallet loaded.'); return;
    }
    const amountStr = String(amountInput).trim();
    if (!amountStr || parseFloat(amountStr) <= 0) {
      toast.error('Please enter a positive amount.'); return;
    }
    const amount = parseFloat(amountStr);
    setLoading(true);
    setError(null);

    await toast.promise(
       fetch(
        `${API_URL}/wallet/${encodeURIComponent(wallet.wallet_id)}/${type}`,
        { // Ensure method and body are here
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: amount.toFixed(2) }),
        }
      )
      .then(async (response) => {
         const responseBody = await response.json();
         if (!response.ok) {
            const apiErrorMsg = responseBody?.message || `HTTP error! Status: ${response.status}`;
            throw new Error(apiErrorMsg);
         }
         return responseBody;
      }),
    {
      loading: `${type === 'credit' ? 'Depositing' : 'Withdrawing'}...`,
      success: (responseBody) => {
         // Move logic inside success handler
         setWallet((prevWallet) => ({ ...prevWallet, balance: responseBody.balance }));
         setAmountInput('');
         refreshWalletAndHistory(); // Trigger refresh
         return <b>Transaction successful! New balance: {formatCurrency(responseBody.balance)}</b>;
      },
      error: (err) => <b>{`Failed to ${type}: ${err.message}`}</b>,
    }
  );
  setLoading(false);
  };
  // --- End Wallet Action Functions ---

  // --- Wrapper for Fetch Wallet Button Click ---
  const onFetchClick = () => {
    // Wrap the silent handleFetchWallet in a toast.promise
    toast.promise(
        handleFetchWallet(walletIdInput), // Call the silent function
        {
            loading: 'Fetching wallet...',
            success: (data) => <b>Wallet {data.wallet_id.substring(0,8)}... loaded!</b>,
            error: (err) => <b>{err.message}</b>, // Error is already set inline
        }
    );
  };

  // --- Function to render content based on active tab ---
  const renderTabContent = () => {
    switch (activeTab) {
      case 'wallet':
        return (
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mb-8 shadow-sm">
            <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Digital Wallet</h2>
            <div className="flex flex-wrap gap-3 mb-4 items-stretch">
            <input
                type="text"
                value={walletIdInput}
                onChange={(e) => setWalletIdInput(e.target.value)}
                placeholder="Enter Wallet ID"
                disabled={loading}
                className="flex-grow basis-60 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
            />
            {/* --- UPDATE onClick HANDLER --- */}
            <button
                onClick={onFetchClick} // Use the new wrapper function
                disabled={loading || !walletIdInput}
                className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed flex-shrink-0"
            >
                {loading && !wallet ? 'Fetching...' : 'Fetch Wallet'}
            </button>
            </div>
             <p className="text-center text-neutral-500 my-4">Or</p>
            <div className="text-center">
            <button
                onClick={handleCreateWallet}
                disabled={loading}
                className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed"
            >
                 {loading && !wallet ? 'Creating...' : 'Create New Wallet'}
            </button>
            </div>

            {wallet && (
                 <div className="mt-6 p-4 bg-primary-blue-light/20 border border-primary-blue/30 rounded-md text-left">
                    <h3 className="text-lg font-semibold text-primary-blue-dark mb-3">Wallet Details</h3>
                    <p className="text-sm mb-1 break-words">
                        <strong className="text-neutral-600">Wallet ID:</strong>
                        <span className="ml-2 font-mono text-primary-blue-dark">{wallet.wallet_id}</span>
                    </p>
                    <p className="text-sm mb-1">
                        <strong className="text-neutral-600">Balance:</strong>
                        <span className="ml-2 font-mono text-primary-blue-dark">{formatCurrency(wallet.balance)}</span>
                    </p>
                    <p className="text-sm">
                        <strong className="text-neutral-600">Currency:</strong>
                        <span className="ml-2 font-mono text-primary-blue-dark">{wallet.currency}</span>
                    </p>
                    <div className="mt-5 pt-4 border-t border-primary-blue/30">
                        <h4 className="text-md font-semibold text-neutral-700 mb-3">Make a Transaction</h4>
                        <div className="mb-3">
                            <input
                            type="number"
                            value={amountInput}
                            onChange={(e) => setAmountInput(e.target.value)}
                            placeholder="Enter amount"
                            disabled={loading}
                            min="0.01" step="0.01"
                            className="w-full p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
                            />
                        </div>
                        <div className="flex justify-center gap-3 mt-2">
                            <button
                                onClick={() => handleTransaction('credit')}
                                disabled={loading || !amountInput}
                                className="px-4 py-2 bg-accent-green text-white rounded-md hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-2 disabled:bg-accent-green-light disabled:cursor-not-allowed"
                            >
                                Credit
                            </button>
                            <button
                                onClick={() => handleTransaction('debit')}
                                disabled={loading || !amountInput}
                                className="px-4 py-2 bg-accent-red text-white rounded-md hover:bg-accent-red-dark focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 disabled:bg-accent-red-light disabled:cursor-not-allowed"
                            >
                                Debit
                            </button>
                        </div>
                    </div>
                    <TransactionHistory
                        key={transactionCount}
                        walletId={wallet.wallet_id}
                        apiUrl={API_URL}
                    />
                </div>
            )}
            {loading && activeTab === 'wallet' && <p className="text-center text-primary-blue mt-4">Processing Wallet Action...</p>}
          </div>
        );
      case 'savings':
        return <SavingsGoals
                  walletId={wallet ? wallet.wallet_id : null}
                  apiUrl={API_URL}
                  onGoalFunded={refreshWalletAndHistory}
                />;
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
    <div className="max-w-3xl mx-auto my-8 p-8 bg-white rounded-lg shadow-md text-neutral-800">
      <Toaster position="top-center" reverseOrder={false} />
      
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
        {/* General Error Display */}
        {error && <p className="mb-4 p-3 bg-accent-red-light border border-accent-red text-accent-red-dark rounded-md text-sm text-left">{error}</p>}

        {/* Render the content for the active tab */}
        {renderTabContent()}
      </main>
    </div>
  );
}

export default App;