import React, { useState, useEffect } from 'react';

// Helper to format currency
const formatCurrency = (amount) => {
  // Use try-catch for robustness if amount might be invalid
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  } catch (e) {
    return String(amount); // Fallback to string
  }
};

function PaymentSimulator({ walletId, apiUrl }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [merchantId, setMerchantId] = useState('');
  const [transactionToCheck, setTransactionToCheck] = useState('');
  const [checkedTransaction, setCheckedTransaction] = useState(null);
  const [pollingIntervalId, setPollingIntervalId] = useState(null); // For auto-refresh

  // --- Fetch transactions when walletId changes ---
  useEffect(() => {
    if (walletId) {
      fetchTransactions();
    } else {
      setTransactions([]); // Clear if no wallet ID
    }

    // Cleanup polling on component unmount or walletId change
    return () => {
      if (pollingIntervalId) {
        clearInterval(pollingIntervalId);
        setPollingIntervalId(null);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]); // Dependency array includes walletId

  // --- Fetch Transactions Function (Placeholder - Needs Backend Endpoint) ---
  const fetchTransactions = async () => {
    if (!walletId) return;
    setLoading(true);
    setError(null);
    try {
      // NOTE: We haven't built a "get transactions by wallet" endpoint yet!
      // This is a placeholder. We'll need to add this endpoint to the
      // payment_processor module later. For now, it will just show empty.
      console.warn("fetchTransactions: 'GET /payment/by-wallet/{id}' endpoint not yet implemented.");
      // Example call if endpoint existed:
      // const response = await fetch(`${apiUrl}/payment/by-wallet/${encodeURIComponent(walletId)}`);
      // if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
      // const data = await response.json();
      // data.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
      // setTransactions(data);
      setTransactions([]); // Temporarily set to empty
    } catch (e) {
      setError(`Failed to fetch transactions: ${e.message}`);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  // --- Initiate Payment Function ---
  const handleRequestPayment = async (e) => {
    e.preventDefault();
    if (!walletId || !paymentAmount || !merchantId || parseFloat(paymentAmount) <= 0) {
      setError('Please provide a valid amount and merchant ID.');
      return;
    }
    setLoading(true);
    setError(null);
    setCheckedTransaction(null); // Clear any previously checked transaction
    try {
      const response = await fetch(`${apiUrl}/payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_id: walletId,
          amount: parseFloat(paymentAmount).toFixed(2),
          merchant_id: merchantId,
        }),
      });

      // Check if response is JSON before parsing
      const contentType = response.headers.get("content-type");
      let responseBody;
      if (contentType && contentType.indexOf("application/json") !== -1) {
          responseBody = await response.json();
      } else {
          // Handle non-JSON responses if necessary, or just read text
          const textResponse = await response.text();
          throw new Error(`Unexpected response format. Status: ${response.status}. Body: ${textResponse}`);
      }

      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }

      const pendingTx = responseBody.transaction;
      setPaymentAmount('');
      setMerchantId('');
      // Add the new pending transaction optimistically
      setTransactions(prev => [pendingTx, ...prev.filter(tx => tx.transaction_id !== pendingTx.transaction_id)]);
      // Start polling for this transaction's status
      startPolling(pendingTx.transaction_id);

    } catch (e) {
      setError(`Failed to initiate payment: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // --- Check Specific Transaction Status Function ---
  const handleCheckTransaction = async (txIdToCheck) => {
     const txId = txIdToCheck || transactionToCheck;
     if (!txId) {
         setError('Please enter a Transaction ID to check.');
         return;
     }
    setLoading(true);
    setError(null);
    setCheckedTransaction(null);
    try {
      const response = await fetch(`${apiUrl}/payment/${encodeURIComponent(txId)}`);
      const responseBody = await response.json(); // Assume API always returns JSON

      if (!response.ok) {
        if (response.status === 404) {
           throw new Error(`Transaction ID ${txId} not found.`);
        }
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      setCheckedTransaction(responseBody);
      // Update the list if this transaction is already there
      setTransactions(prev => prev.map(tx => tx.transaction_id === txId ? responseBody : tx));
      // Stop polling if we manually checked and it's completed
      if (responseBody.status !== 'PENDING' && pollingIntervalId) {
         stopPolling();
      }
    } catch (e) {
      setError(`Failed to check transaction: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // --- Polling Logic ---
  const startPolling = (txId) => {
    // Clear any existing interval
    stopPolling();

    console.log(`Starting polling for transaction: ${txId}`);
    const intervalId = setInterval(async () => {
      console.log(`Polling status for ${txId}...`);
      try {
        const response = await fetch(`${apiUrl}/payment/${encodeURIComponent(txId)}`);
         if (!response.ok) {
             // If fetch fails (e.g., 404), stop polling
             console.error(`Polling failed for ${txId}. Status: ${response.status}`);
             stopPolling();
             // Optionally set an error state here
             return;
         }
        const data = await response.json();
        // Update the specific transaction in the list
        setTransactions(prev => prev.map(tx => tx.transaction_id === txId ? data : tx));

        // If status is no longer PENDING, stop polling
        if (data.status !== 'PENDING') {
          console.log(`Transaction ${txId} completed with status: ${data.status}. Stopping polling.`);
          stopPolling();
        }
      } catch (error) {
        console.error(`Error during polling for ${txId}:`, error);
        stopPolling(); // Stop polling on error
        // Optionally set an error state
      }
    }, 5000); // Poll every 5 seconds

    setPollingIntervalId(intervalId);
  };

  const stopPolling = () => {
    if (pollingIntervalId) {
      clearInterval(pollingIntervalId);
      setPollingIntervalId(null);
      console.log("Polling stopped.");
    }
  };


  // --- Render Logic ---
  if (!walletId) {
    return null; // Don't render if no wallet is active
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-gray-700 mb-6 text-center">Payment Simulator</h2>

      {/* --- Loading and Error Display --- */}
      {loading && <p className="text-center text-blue-600 my-4">Processing...</p>}
      {error && (
        <p className="my-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm text-left">
          {error}
        </p>
      )}

      {/* --- Form to Initiate Payment --- */}
      <form onSubmit={handleRequestPayment} className="mb-6 pb-4 border-b border-gray-200">
        <h4 className="text-md font-semibold text-gray-700 mb-3">Make a Payment</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input
            type="number"
            value={paymentAmount}
            onChange={(e) => setPaymentAmount(e.target.value)}
            placeholder="Amount ($)"
            disabled={loading}
            min="0.01" step="0.01" required
            className="p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
          />
          <input
            type="text"
            value={merchantId}
            onChange={(e) => setMerchantId(e.target.value)}
            placeholder="Merchant ID (e.g., store-abc)"
            disabled={loading}
            required
            className="p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 md:col-span-2" // Take more space on medium screens
          />
        </div>
        <div className="text-center">
          <button
            type="submit"
            disabled={loading || !paymentAmount || !merchantId}
            className="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:bg-purple-300"
          >
            {loading ? 'Processing...' : 'Submit Payment'}
          </button>
        </div>
      </form>

      {/* --- Check Specific Transaction --- */}
      <div className="mb-6 pb-4 border-b border-gray-200">
          <h4 className="text-md font-semibold text-gray-700 mb-3">Check Transaction Status</h4>
          <div className="flex flex-wrap gap-3 mb-4 items-stretch">
              <input
                  type="text"
                  value={transactionToCheck}
                  onChange={(e) => setTransactionToCheck(e.target.value)}
                  placeholder="Enter Transaction ID"
                  disabled={loading}
                  className="flex-grow basis-60 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 min-w-[150px]"
              />
              <button
                  onClick={() => handleCheckTransaction()}
                  disabled={loading || !transactionToCheck}
                  className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:bg-gray-300 flex-shrink-0"
              >
                  {loading ? 'Checking...' : 'Check Status'}
              </button>
          </div>
          {checkedTransaction && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md text-xs">
                  <p>Status for {checkedTransaction.transaction_id}:
                      <span className={`ml-2 font-semibold ${
                          checkedTransaction.status === 'SUCCESSFUL' ? 'text-green-700' :
                          checkedTransaction.status === 'FAILED' ? 'text-red-700' :
                          'text-yellow-700' // PENDING
                      }`}>
                          {checkedTransaction.status}
                      </span>
                  </p>
                  {/* Optionally display more details */}
              </div>
          )}
      </div>

      {/* --- Display Recent Transactions --- */}
      <div>
        <h4 className="text-md font-semibold text-gray-700 mb-3">Recent Transactions</h4>
        {!loading && transactions.length === 0 && (
          <p className="text-center text-gray-500 my-4">No recent transactions to display. (Endpoint not implemented or none found).</p>
        )}
        {!loading && transactions.length > 0 && (
          <div className="space-y-3">
            {transactions.map((tx) => (
              <div key={tx.transaction_id} className="p-3 bg-white border border-gray-200 rounded-md shadow-sm text-sm">
                <div className="flex justify-between items-center mb-1">
                  <span className={`font-medium px-2 py-0.5 rounded text-xs ${
                      tx.status === 'SUCCESSFUL' ? 'bg-green-100 text-green-800' :
                      tx.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800' // PENDING
                  }`}>
                      {tx.status}
                  </span>
                  <span className="text-gray-600">{formatCurrency(tx.amount)}</span>
                </div>
                 <p className="text-xs text-gray-500">To: {tx.merchant_id}</p>
                 <p className="text-xs text-gray-400 mt-1 truncate">ID: {tx.transaction_id}</p>
                 {tx.updated_at && (
                    <p className="text-xs text-gray-400">Updated: {new Date(tx.updated_at * 1000).toLocaleString()}</p>
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