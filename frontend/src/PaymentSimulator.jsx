import React, { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import Spinner from './Spinner';
import { useWallet, formatCurrency } from './contexts/WalletContext';
import { ClipboardDocumentListIcon } from '@heroicons/react/24/outline';
import WalletPrompt from './WalletPrompt';

function PaymentSimulator() {
  // --- 1. Get auth and wallet state ---
  const { wallet, apiUrl, refreshWalletAndHistory, authorizedFetch } = useWallet();
  const walletId = wallet ? wallet.wallet_id : null;

  // --- 2. State for this component ---
  const [transactions, setTransactions] = useState([]);
  const [loadingList, setLoadingList] = useState(false); // For the list
  const [loadingAction, setLoadingAction] = useState(false); // For the form button
  const [merchant, setMerchant] = useState('DemoMerchant');
  const [amount, setAmount] = useState('50.00');
  
  // State for manual status check
  const [txIdToCheck, setTxIdToCheck] = useState('');
  const [checkedTxStatus, setCheckedTxStatus] = useState(null);

  // Ref to hold all active polling intervals
  const pollingIntervals = useRef(new Map());

  // --- 3. API-calling functions ---
  const fetchTransactions = useCallback(async () => {
    if (!walletId || !authorizedFetch) return;
    setLoadingList(true);
    try {
      const response = await authorizedFetch(`${apiUrl}/payment/by-wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || 'Failed to fetch transactions');
      }
      const data = await response.json();
      setTransactions(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(err.message);
      setTransactions([]);
    } finally {
      setLoadingList(false);
    }
  }, [walletId, apiUrl, authorizedFetch]);

  useEffect(() => {
    fetchTransactions();
    // Clear all polling intervals when component unmounts or wallet changes
    return () => {
      pollingIntervals.current.forEach(intervalId => clearInterval(intervalId));
      pollingIntervals.current.clear();
    };
  }, [fetchTransactions]);

  // Handler for the "Submit Payment" button
  const handleRequestPayment = async (e) => {
    e.preventDefault();
    const amountNum = parseFloat(amount);
    if (!merchant || isNaN(amountNum) || amountNum <= 0) {
      toast.error("Please enter a valid merchant and positive amount.");
      return;
    }
    
    setLoadingAction(true);
    try {
      const response = await authorizedFetch(`${apiUrl}/payment`, {
        method: 'POST',
        body: JSON.stringify({
          wallet_id: walletId,
          merchant_id: merchant,
          amount: amountNum.toFixed(2)
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Payment request failed');
      }
      
      toast.success(data.message);
      setTransactions(prev => [data.transaction, ...prev]);
      pollForStatus(data.transaction_id); // Start polling for this new transaction
      
      // Refresh wallet after a delay (to allow debit)
      setTimeout(refreshWalletAndHistory, 4000);
      
    } catch (err) {
      toast.error(`Error: ${err.message}`);
    } finally {
      setLoadingAction(false);
    }
  };

  // Handler for the "Check Status" button
  const handleCheckTransaction = async () => {
    if (!txIdToCheck) return;
    setLoadingAction(true);
    setCheckedTxStatus(null);
    try {
      const status = await checkPaymentStatus(txIdToCheck);
      setCheckedTxStatus({ id: txIdToCheck, status: status });
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoadingAction(false);
    }
  };

  // --- 4. Polling functions (using authorizedFetch) ---
  
  const checkPaymentStatus = async (txId) => {
    try {
      const response = await authorizedFetch(`${apiUrl}/payment/${encodeURIComponent(txId)}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Status check failed');
      }
      return data.status;
    } catch (err) {
      console.error(`Poll error: ${err.message}`);
      throw err; // Re-throw to be caught by handlers
    }
  };
  
  const pollForStatus = (txId) => {
    // If we are already polling this tx, don't start another
    if (pollingIntervals.current.has(txId)) return;

    console.log(`Starting polling for transaction: ${txId}`);
    const intervalId = setInterval(async () => {
      console.log(`Polling status for ${txId}...`);
      try {
        const status = await checkPaymentStatus(txId);

        // Update the transaction in our list
        setTransactions(prev => 
          prev.map(tx => tx.transaction_id === txId ? { ...tx, status: status } : tx)
        );

        if (status !== 'PENDING') {
          console.log(`Transaction ${txId} completed with status: ${status}. Stopping polling.`);
          stopPolling(txId);
          toast.success(`Payment ${txId.substring(0, 8)}... ${status.toLowerCase()}!`);
          
          if (status === 'SUCCESSFUL' && refreshWalletAndHistory) {
              refreshWalletAndHistory();
          }
        }
      } catch (error) {
        console.error(`Error during polling for ${txId}:`, error);
        stopPolling(txId);
        toast.error(`Error polling for ${txId}: ${error.message}`);
      }
    }, 5000); // Poll every 5 seconds

    pollingIntervals.current.set(txId, intervalId);
  };

  const stopPolling = (txId) => {
    if (pollingIntervals.current.has(txId)) {
      clearInterval(pollingIntervals.current.get(txId));
      pollingIntervals.current.delete(txId);
      console.log(`Polling stopped for ${txId}.`);
    }
  };
  // ---

  // --- 5. Render Logic ---
  if (!walletId) {
      return <WalletPrompt />;
  }

  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Payment Simulator</h2>

      {/* Form to Initiate Payment */}
      <form onSubmit={handleRequestPayment} className="mb-6 pb-4 border-b border-neutral-200">
        <h4 className="text-md font-semibold text-neutral-700 mb-3">Make a Payment</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Amount ($)"
            disabled={loadingAction}
            min="0.01" step="0.01" required
            className="p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
          />
          <input
            type="text"
            value={merchant}
            onChange={(e) => setMerchant(e.target.value)}
            placeholder="Merchant ID"
            disabled={loadingAction}
            required
            className="p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 md:col-span-2"
          />
        </div>
        <div className="text-center">
          <button
            type="submit"
            disabled={loadingAction || !amount || !merchant}
            className="px-4 py-2 w-32 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:bg-indigo-300 disabled:cursor-not-allowed"
          >
            {loadingAction ? <Spinner mini={true} /> : 'Submit Payment'}
          </button>
        </div>
      </form>

      {/* Check Specific Transaction */}
      <div className="mb-6 pb-4 border-b border-neutral-200">
        <h4 className="text-md font-semibold text-neutral-700 mb-3">Check Transaction Status</h4>
        <div className="flex flex-wrap gap-3 mb-4 items-stretch">
          <input
            type="text"
            value={txIdToCheck}
            onChange={(e) => setTxIdToCheck(e.target.value)}
            placeholder="Enter Transaction ID"
            disabled={loadingAction}
            className="flex-grow basis-60 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
          />
          <button
            onClick={handleCheckTransaction}
            disabled={loadingAction || !txIdToCheck}
            className="px-4 py-2 w-32 bg-neutral-500 text-white rounded-md hover:bg-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-500 focus:ring-offset-2 disabled:bg-neutral-300 disabled:cursor-not-allowed flex-shrink-0"
          >
            {loadingAction ? <Spinner mini={true} /> : 'Check Status'}
          </button>
        </div>
        {checkedTxStatus && (
          <div className="mt-4 p-3 bg-primary-blue-light/20 border border-primary-blue/30 rounded-md text-xs">
            <p className="text-neutral-700">Status for {checkedTxStatus.id.substring(0, 8)}...:
              <span className={`ml-2 font-semibold ${
                checkedTxStatus.status === 'SUCCESSFUL' ? 'text-accent-green-dark' :
                checkedTxStatus.status === 'FAILED' ? 'text-accent-red-dark' :
                'text-yellow-600'
              }`}>
                {checkedTxStatus.status}
              </span>
            </p>
          </div>
        )}
      </div>

      {/* Display Recent Transactions */}
      <div>
        <h4 className="text-md font-semibold text-neutral-700 mb-3">Recent Transactions</h4>
        {loadingList && <Spinner />}

        {!loadingList && transactions.length === 0 && (
          <div className="text-center text-neutral-500 my-4 py-6">
            <ClipboardDocumentListIcon className="h-10 w-10 mx-auto text-neutral-400" />
            <h3 className="mt-2 text-sm font-semibold text-neutral-700">No Payment History</h3>
            <p className="mt-1 text-sm text-neutral-500">Make a payment using the form above to see it here.</p>
          </div>
        )}

        {!loadingList && transactions.length > 0 && (
          <div className="space-y-3 max-h-60 overflow-y-auto pr-2">
            {transactions.map((tx) => (
              <div key={tx.transaction_id} className="p-3 bg-white border border-neutral-200 rounded-md shadow-sm text-sm">
                <div className="flex justify-between items-center mb-1">
                  <span className={`font-medium px-2 py-0.5 rounded text-xs ${
                    tx.status === 'SUCCESSFUL' ? 'bg-accent-green-light text-accent-green-dark' :
                    tx.status === 'FAILED' ? 'bg-accent-red-light text-accent-red-dark' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {tx.status}
                  </span>
                  <span className="text-neutral-600 font-semibold">{formatCurrency(tx.amount)}</span>
                </div>
                <p className="text-xs text-neutral-500">To: {tx.merchant_id}</p>
                <p className="text-xs text-neutral-400 mt-1 truncate">ID: {tx.transaction_id}</p>
                {tx.updated_at && (
                  <p className="text-xs text-neutral-400">Updated: {new Date(tx.updated_at * 1000).toLocaleString()}</p>
                )}
                {/* Show polling indicator */}
                {pollingIntervals.current.has(tx.transaction_id) && tx.status === 'PENDING' && (
                  <p className="text-xs text-blue-500 animate-pulse">Checking status...</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default PaymentSimulator;