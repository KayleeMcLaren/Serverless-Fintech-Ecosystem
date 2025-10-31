import React, { useState } from 'react'; // Import useState for local error
import { toast } from 'react-hot-toast';
import TransactionHistory from './TransactionHistory';
import Spinner from './Spinner';
// Import the context hook and shared helper
import { useWallet, formatCurrency } from './contexts/WalletContext';

function Wallet() {
  const {
    wallet,
    walletIdInput,
    setWalletIdInput,
    amountInput,
    setAmountInput,
    loading,
    transactionCount,
    handleFetchWallet,
    handleTransaction,
    apiUrl,
    emailInput,
    setEmailInput,
    onboardingStatus,
    handleApplyForAccount
  } = useWallet();

  // --- NEW: Local state for inline validation ---
  const [amountError, setAmountError] = useState('');

  // --- NEW: Validation function ---
  const validateAmount = (amountStr) => {
    const amount = parseFloat(amountStr);
    if (!amountStr || isNaN(amount) || amount <= 0) {
      setAmountError('Please enter a positive amount.');
      return false;
    }
    setAmountError(''); // Clear error
    return true;
  };

  // --- NEW: onChange handler for amount input ---
  const handleAmountInputChange = (e) => {
    const value = e.target.value;
    setAmountInput(value); // Update the global context
    validateAmount(value); // Validate on every change
  };

  // --- NEW: Wrapper for transaction button click ---
  const onTransactionClick = (type) => {
    // Run validation one last time on submit
    if (validateAmount(amountInput)) {
      // If valid, call the context function
      handleTransaction(type);
    }
    // If invalid, the error message is already visible
  };
  
  // --- Wrapper for Fetch Wallet Button Click ---
  const onFetchClick = () => {
    // Wrap the silent handleFetchWallet in a toast.promise
    toast.promise(
        handleFetchWallet(walletIdInput), // Call the function from context
        {
            loading: 'Fetching wallet...',
            success: (data) => <b>Wallet {data.wallet_id.substring(0,8)}... loaded!</b>,
            error: (err) => <b>{err.message}</b>,
        }
    ).catch(() => {});
  };

  // --- This is the JSX moved from App.jsx ---
  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mb-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Digital Wallet</h2>
       {/* Input group for fetching wallet */}
      <div className="flex flex-wrap gap-3 mb-4 items-stretch">
      <input
          type="text"
          value={walletIdInput}
          onChange={(e) => setWalletIdInput(e.target.value)}
          placeholder="Enter Existing Wallet ID"
          disabled={loading || onboardingStatus}
          className="flex-grow basis-60 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
      />
      <button
          onClick={onFetchClick} // Use the toast-wrapper
          disabled={loading || onboardingStatus || !walletIdInput}
          className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed flex-shrink-0"
      >
          {loading && !wallet ? 'Fetching...' : 'Fetch Wallet'}
      </button>
      </div>
       <p className="text-center text-neutral-500 my-4">Or</p>

      {/* --- NEW: Onboarding / Create Account Form --- */}
      <div className="text-center">
        <h3 className="text-lg font-semibold text-neutral-700 mb-3">Create a New Account</h3>
        <div className="flex flex-wrap gap-3 items-stretch justify-center">
            <input
                type="email"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                placeholder="Enter your (mock) email"
                disabled={loading || onboardingStatus}
                className="flex-grow basis-60 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
            />
            <button
                onClick={handleApplyForAccount}
                disabled={loading || onboardingStatus || !emailInput}
                className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed flex-shrink-0"
            >
                 {loading ? 'Applying...' : 'Apply for Account'}
            </button>
        </div>
      </div>
      {/* --- END NEW FORM --- */}
      
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
                  <div className="mb-1"> {/* Reduced margin-bottom */}
                      <input
                      type="number"
                      value={amountInput}
                      onChange={handleAmountInputChange} // Use new handler
                      placeholder="Enter amount"
                      disabled={loading}
                      min="0.01" step="0.01"
                      // Add red border if error exists
                      className={`w-full p-2 border rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 ${
                        amountError ? 'border-accent-red' : 'border-neutral-300'
                      }`}
                      />
                      {/* --- NEW: Render inline error message --- */}
                      {amountError && (
                          <p className="text-xs text-accent-red-dark mt-1">{amountError}</p>
                      )}
                  </div>
                  <div className="flex justify-center gap-3 mt-2">
                      <button
                          onClick={() => onTransactionClick('credit')} // Use new handler
                          disabled={loading || !!amountError || !amountInput} // Disable if error or no input
                          className="px-4 py-2 bg-accent-green text-white rounded-md hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-2 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                      >
                          Credit
                      </button>
                      <button
                          onClick={() => onTransactionClick('debit')} // Use new handler
                          disabled={loading || !!amountError || !amountInput} // Disable if error or no input
                          className="px-4 py-2 bg-accent-red text-white rounded-md hover:bg-accent-red-dark focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                      >
                          Debit
                      </button>
                  </div>
              </div>
              {/* Transaction History - Pass key from context */}
              <TransactionHistory
                        key={transactionCount} // Keep key to force re-render
                    />
          </div>
      )}
      {/* Show loading spinner if wallet is loading */}
      {loading && !wallet && <Spinner />}
    </div>
  );
}

export default Wallet;