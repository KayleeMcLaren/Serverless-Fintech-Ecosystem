import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import TransactionHistory from './TransactionHistory';
import Spinner from './Spinner';
import { useWallet, formatCurrency } from './contexts/WalletContext';

function Wallet() {
  const {
    wallet,
    walletIdInput,
    setWalletIdInput,
    amountInput,
    setAmountInput,
    loading,
    onboardingStatus,
    handleApplyForAccount,
    handleFetchWallet,
    handleTransaction,
    emailInput,
    setEmailInput,
  } = useWallet();

  const [amountError, setAmountError] = useState('');
 const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // (All helper functions: validateAmount, handleAmountInputChange, etc. - no changes)
  const validateAmount = (amountStr) => {
    const amount = parseFloat(amountStr);
    if (!amountStr || isNaN(amount) || amount <= 0) {
      setAmountError('Please enter a positive amount.');
      return false;
    }
    setAmountError('');
    return true;
  };
  const handleAmountInputChange = (e) => {
    const value = e.target.value;
    setAmountInput(value);
    validateAmount(value);
  };
  const onTransactionClick = (type) => {
    if (validateAmount(amountInput)) {
      handleTransaction(type);
    }
  };
  const onFetchClick = () => {
    toast.promise(
        handleFetchWallet(walletIdInput),
        {
            loading: 'Fetching wallet...',
            success: (data) => <b>Wallet {data.wallet_id.substring(0,8)}... loaded!</b>,
            error: (err) => <b>{err.message}</b>,
        }
    ).catch(() => {});
  };

  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mb-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Digital Wallet</h2>
       
      {/* --- Load Existing Wallet --- */}
      <div className="flex flex-wrap gap-3 mb-4 items-stretch">
        {/* ... (input and button) ... */}
         <input
            type="text"
            value={walletIdInput}
            onChange={(e) => setWalletIdInput(e.target.value)}
            placeholder="Enter Existing Wallet ID"
            disabled={loading || onboardingStatus}
            className="flex-grow basis-60 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
        />
        <button
            onClick={onFetchClick}
            disabled={loading || onboardingStatus || !walletIdInput}
            className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed flex-shrink-0"
        >
            {loading && !wallet ? 'Fetching...' : 'Fetch Wallet'}
        </button>
      </div>

       <p className="text-center text-neutral-500 my-4">Or</p>

       {/* --- Create Account Form --- */}
      <div className="text-center">
        {/* ... (input and button) ... */}
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
      
      {/* Wallet Details and Transactions - Only if wallet exists */}
      {wallet && (
           <div className="mt-6 p-4 bg-primary-blue-light/20 border border-primary-blue/30 rounded-md text-left">
              
              {/* --- Wallet Details (THIS IS THE FIX) --- */}
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-primary-blue-dark">Wallet Details</h3>
                <span className="text-sm font-medium text-primary-blue-dark">ID: {wallet.wallet_id.substring(0, 8)}...</span>
              </div>

              {/* Balance */}
              <div className="flex justify-between items-baseline mt-3">
                <span className="text-lg font-semibold text-primary-blue-dark">Balance:</span>
                <span className="text-2xl font-bold text-primary-blue-dark">{formatCurrency(wallet.balance)}</span>
              </div>
               
              {/* --- Transaction Section --- */}
              <div className="mt-5 pt-4 border-t border-primary-blue/30">
                  <h4 className="text-md font-semibold text-neutral-700 mb-3">Make a Transaction</h4>
                  <div className="mb-1">
                      <input
                        type="number"
                        value={amountInput}
                        onChange={handleAmountInputChange}
                        placeholder="Enter amount"
                        disabled={loading}
                        min="0.01" step="0.01"
                        className={`w-full p-2 border rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 ${
                          amountError ? 'border-accent-red' : 'border-neutral-300'
                        }`}
                      />
                      {amountError && (
                          <p className="text-xs text-accent-red-dark mt-1">{amountError}</p>
                      )}
                  </div>
                  <div className="flex justify-center gap-3 mt-2">
                      <button
                          onClick={() => onTransactionClick('credit')}
                          disabled={loading || !!amountError || !amountInput}
                          className="px-4 py-2 bg-accent-green text-white rounded-md hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-2 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                      >
                          Credit
                      </button>
                      <button
                          onClick={() => onTransactionClick('debit')}
                          disabled={loading || !!amountError || !amountInput}
                          className="px-4 py-2 bg-accent-red text-white rounded-md hover:bg-accent-red-dark focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                      >
                          Debit
                      </button>
                  </div>
              </div>

              {/* --- Transaction History Section --- */}
              <div className="mt-5 pt-4 border-t border-primary-blue/30">
                <button
                  onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                  className="text-xs font-semibold text-primary-blue hover:text-primary-blue-dark"
                >
                  {isHistoryOpen ? 'Hide Transaction History' : 'Show Transaction History'}
                </button>
                  
                {isHistoryOpen && (
                  <div className="mt-2">
                    <TransactionHistory />
                  </div>
                )}
              </div>
           </div>    
        )}
      {loading && !wallet && <Spinner />}
    </div>
  );
}

export default Wallet;