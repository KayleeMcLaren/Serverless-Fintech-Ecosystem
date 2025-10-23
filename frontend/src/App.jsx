import React, { useState } from 'react';
import { Toaster, toast } from 'react-hot-toast';
// Import Components
import SavingsGoals from './SavingsGoals';
import MicroLoans from './MicroLoans';
import PaymentSimulator from './PaymentSimulator';
import DebtOptimiser from './DebtOptimiser';
import TransactionHistory from './TransactionHistory';
import Spinner from './Spinner';
// Import Icons
import {
  WalletIcon, BanknotesIcon, CreditCardIcon, ArrowsRightLeftIcon, ScaleIcon
} from '@heroicons/react/24/outline';
// Import the context hook and shared helper
import { useWallet, formatCurrency } from './contexts/WalletContext';

function App() {
  const [activeTab, setActiveTab] = useState('wallet');
  // Error state is now managed *per component* or via toasts
  // We can add a global error here if needed, but let's rely on toasts for now.
  // const [error, setError] = useState(null); 

  // --- Get ALL wallet state and functions from the context ---
  const {
    wallet,
    walletIdInput,
    setWalletIdInput,
    amountInput,
    setAmountInput,
    loading,
    transactionCount,
    handleCreateWallet,
    handleFetchWallet, // The silent fetch
    handleTransaction,
    apiUrl,
  } = useWallet();
  // --- End Get State ---


  // --- Wrapper for Fetch Wallet Button Click ---
  // This function adds the toast.promise wrapper to the silent fetch function
  const onFetchClick = () => {
    toast.promise(
        handleFetchWallet(walletIdInput), // Call the function from context
        {
            loading: 'Fetching wallet...',
            success: (data) => <b>Wallet {data.wallet_id.substring(0,8)}... loaded!</b>,
            error: (err) => <b>{err.message}</b>, // Error is already set inline
        }
    ).catch(() => {}); // Catch the re-thrown error so it doesn't log to console
  };
  
  // --- Function to render content based on active tab ---
  const renderTabContent = () => {
    switch (activeTab) {
      case 'wallet':
        return (
          // --- This is the Wallet Component JSX ---
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mb-8 shadow-sm">
            <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Digital Wallet</h2>
            
            {/* Input group for fetching wallet */}
            <div className="flex flex-wrap gap-3 mb-4 items-stretch">
              <input
                  type="text"
                  value={walletIdInput} // Get from context
                  onChange={(e) => setWalletIdInput(e.target.value)} // Set in context
                  placeholder="Enter Wallet ID"
                  disabled={loading} // Get from context
                  className="flex-grow basis-60 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
              />
              <button
                  onClick={onFetchClick} // Use the toast-wrapper
                  disabled={loading || !walletIdInput}
                  className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed flex-shrink-0"
              >
                  {loading && !wallet ? 'Fetching...' : 'Fetch Wallet'}
              </button>
            </div>

            <p className="text-center text-neutral-500 my-4">Or</p>

            {/* Create Button */}
            <div className="text-center">
              <button
                  onClick={handleCreateWallet} // Get from context
                  disabled={loading}
                  className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed"
              >
                  {loading && !wallet ? 'Creating...' : 'Create New Wallet'}
              </button>
            </div>

            {/* Wallet Details and Transactions - Only if wallet exists */}
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
                     
                     {/* Transaction Section */}
                    <div className="mt-5 pt-4 border-t border-primary-blue/30">
                        <h4 className="text-md font-semibold text-neutral-700 mb-3">Make a Transaction</h4>
                        <div className="mb-3">
                            <input
                            type="number"
                            value={amountInput} // Get from context
                            onChange={(e) => setAmountInput(e.target.value)} // Set in context
                            placeholder="Enter amount"
                            disabled={loading}
                            min="0.01" step="0.01"
                            className="w-full p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
                            />
                        </div>
                        <div className="flex justify-center gap-3 mt-2">
                            <button
                                onClick={() => handleTransaction('credit')} // Get from context
                                disabled={loading || !amountInput}
                                className="px-4 py-2 bg-accent-green text-white rounded-md hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-2 disabled:bg-accent-green-light disabled:cursor-not-allowed"
                            >
                                Credit
                            </button>
                            <button
                                onClick={() => handleTransaction('debit')} // Get from context
                                disabled={loading || !amountInput}
                                className="px-4 py-2 bg-accent-red text-white rounded-md hover:bg-accent-red-dark focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 disabled:bg-accent-red-light disabled:cursor-not-allowed"
                            >
                                Debit
                            </button>
                        </div>
                    </div>

                    {/* Transaction History - Pass key from context */}
                    <TransactionHistory
                        key={transactionCount} // Get from context
                        walletId={wallet.wallet_id}
                        apiUrl={apiUrl} // Get from context
                    />
                </div>
            )}
            {/* Show loading spinner if wallet is loading */}
            {loading && !wallet && <Spinner />}
          </div>
          // --- End Wallet Component JSX ---
        );

      case 'savings':
        // No props needed, SavingsGoals will use useWallet()
        return <SavingsGoals />;
      case 'loans':
        // No props needed, MicroLoans will use useWallet()
        return <MicroLoans />;
      case 'payments':
        // No props needed, PaymentSimulator will use useWallet()
        return <PaymentSimulator />;
      case 'optimiser':
        // No props needed, DebtOptimiser will use useWallet()
        return <DebtOptimiser />;
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
          onClick={() => { setActiveTab(tab.id); }} // Removed setError
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
        {/* General Error Display (Removed - now handled by toasts) */}
        {/* {error && <p ...>{error}</p>} */}

        {/* Render the content for the active tab */}
        {renderTabContent()}
      </main>
    </div>
  );
}

export default App;