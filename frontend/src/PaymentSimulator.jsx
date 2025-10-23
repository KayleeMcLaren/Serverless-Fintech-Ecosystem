import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';

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

function PaymentSimulator({ walletId, apiUrl }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  // const [error, setError] = useState(null); // Replaced by toasts
  const [paymentAmount, setPaymentAmount] = useState('');
  const [merchantId, setMerchantId] = useState('');
  const [transactionToCheck, setTransactionToCheck] = useState('');
  const [checkedTransaction, setCheckedTransaction] = useState(null);
  const pollingIntervalId = useRef(null); // Use useRef

  // --- Fetch transactions when walletId changes ---
  useEffect(() => {
    if (walletId) {
      fetchTransactions();
    } else {
      setTransactions([]);
    }
    // Cleanup polling
    return () => {
      if (pollingIntervalId.current) { // Use .current
        clearInterval(pollingIntervalId.current);
        pollingIntervalId.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]);

   // Fetch Transactions
   const fetchTransactions = async () => {
    if (!walletId) return;
    setListLoading(true);
    try {
      console.warn("fetchTransactions: 'GET /payment/by-wallet/{id}' endpoint not yet implemented.");
      setTransactions([]);
    } catch (e) {
      toast.error(`Fetch transactions failed: ${e.message}`);
      setTransactions([]);
    } finally {
      setListLoading(false);
    }
  };

  // --- Initiate Payment (Use Toast) ---
  const handleRequestPayment = async (e) => {
    e.preventDefault();
    if (!walletId || !paymentAmount || !merchantId || parseFloat(paymentAmount) <= 0) {
      toast.error('Please provide a valid amount and merchant ID.');
      return;
    }
    setLoading(true);
    setCheckedTransaction(null);

    await toast.promise(
        fetch(`${apiUrl}/payment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              wallet_id: walletId,
              amount: parseFloat(paymentAmount).toFixed(2),
              merchant_id: merchantId,
            }),
        })
        .then(async (response) => {
            const contentType = response.headers.get("content-type");
            let responseBody;
            if (contentType && contentType.indexOf("application/json") !== -1) {
                responseBody = await response.json();
            } else {
                const textResponse = await response.text();
                throw new Error(`Unexpected response format. Status: ${response.status}. Body: ${textResponse}`);
            }
            if (!response.ok) {
                throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
            }
            return responseBody;
        })
        .then((responseBody) => {
            const pendingTx = responseBody.transaction;
            setPaymentAmount('');
            setMerchantId('');
            setTransactions(prev => [pendingTx, ...prev.filter(tx => tx.transaction_id !== pendingTx.transaction_id)]);
            startPolling(pendingTx.transaction_id);
        }),
        {
            loading: 'Submitting payment...',
            success: <b>Payment submitted! Processing...</b>,
            error: (err) => <b>Payment failed: {err.message}</b>,
        }
    );
    setLoading(false);
  };

  // --- CORRECTED handleCheckTransaction Function ---
  const handleCheckTransaction = async (txIdToCheck) => {
     const txId = txIdToCheck || transactionToCheck;
     if (!txId) {
         toast.error('Please enter a Transaction ID.');
         return;
     }
    setLoading(true);
    setCheckedTransaction(null);

    await toast.promise(
        fetch(`${apiUrl}/payment/${encodeURIComponent(txId)}`)
        .then(async(response) => {
            // This .then() validates and returns the data
            const responseBody = await response.json();
            if (!response.ok) {
                if (response.status === 404) {
                   throw new Error(`Transaction ID ${txId} not found.`);
                }
                throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
            }
            return responseBody; // Pass transaction data
        }),
        // REMOVED the second .then() block
        {
            loading: 'Checking status...',
            success: (data) => { // `data` is the responseBody
                // --- Move logic from old .then() block HERE ---
                setCheckedTransaction(data);
                setTransactions(prev => prev.map(tx => tx.transaction_id === txId ? data : tx));
                if (data.status !== 'PENDING' && pollingIntervalId.current) { // Use .current
                     stopPolling();
                }
                // --- End logic move ---
                return <b>Status: {data.status}</b>; // Return the toast message
            },
            error: (err) => <b>{err.message}</b>,
        }
    );
    setLoading(false);
  };
  // --- END CORRECTION ---

  // --- Polling Logic (Using useRef) ---
  const startPolling = (txId) => {
    stopPolling();
    console.log(`Starting polling for transaction: ${txId}`);
    const intervalId = setInterval(async () => {
      console.log(`Polling status for ${txId}...`);
      try {
        const response = await fetch(`${apiUrl}/payment/${encodeURIComponent(txId)}`);
         if (!response.ok) {
             console.error(`Polling failed for ${txId}. Status: ${response.status}`);
             stopPolling();
             return;
         }
        const data = await response.json();
        setTransactions(prev => prev.map(tx => tx.transaction_id === txId ? data : tx));
        if (data.status !== 'PENDING') {
          console.log(`Transaction ${txId} completed with status: ${data.status}. Stopping polling.`);
          stopPolling();
          toast.success(`Payment ${data.transaction_id.substring(0,8)}... ${data.status.toLowerCase()}!`);
        }
      } catch (error) {
        console.error(`Error during polling for ${txId}:`, error);
        stopPolling();
        toast.error(`Error polling for ${txId}: ${error.message}`);
      }
    }, 5000);
    pollingIntervalId.current = intervalId; // Set .current
  };

  const stopPolling = () => {
    if (pollingIntervalId.current) { // Check .current
      clearInterval(pollingIntervalId.current); // Clear using .current
      pollingIntervalId.current = null; // Set .current to null
      console.log("Polling stopped.");
    }
  };
  // --- End Polling Logic ---


  // --- Render Logic ---
  if (!walletId) {
    return null;
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
            value={paymentAmount}
            onChange={(e) => setPaymentAmount(e.target.value)}
            placeholder="Amount ($)"
            disabled={loading}
            min="0.01" step="0.01" required
            className="p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
          />
          <input
            type="text"
            value={merchantId}
            onChange={(e) => setMerchantId(e.target.value)}
            placeholder="Merchant ID"
            disabled={loading}
            required
            className="p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 md:col-span-2"
          />
        </div>
        <div className="text-center">
          <button
            type="submit"
            disabled={loading || !paymentAmount || !merchantId}
            className="px-4 py-2 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:bg-indigo-300 disabled:cursor-not-allowed"
          >
            Submit Payment
          </button>
        </div>
      </form>

      {/* Check Specific Transaction */}
      <div className="mb-6 pb-4 border-b border-neutral-200">
          <h4 className="text-md font-semibold text-neutral-700 mb-3">Check Transaction Status</h4>
          <div className="flex flex-wrap gap-3 mb-4 items-stretch">
              <input
                  type="text"
                  value={transactionToCheck}
                  onChange={(e) => setTransactionToCheck(e.target.value)}
                  placeholder="Enter Transaction ID"
                  disabled={loading}
                  className="flex-grow basis-60 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
              />
              <button
                  onClick={() => handleCheckTransaction()}
                  disabled={loading || !transactionToCheck}
                  className="px-4 py-2 bg-neutral-500 text-white rounded-md hover:bg-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-500 focus:ring-offset-2 disabled:bg-neutral-300 disabled:cursor-not-allowed flex-shrink-0"
              >
                  Check Status
              </button>
          </div>
          {checkedTransaction && (
              <div className="mt-4 p-3 bg-primary-blue-light/20 border border-primary-blue/30 rounded-md text-xs">
                  <p className="text-neutral-700">Status for {checkedTransaction.transaction_id.substring(0,8)}...:
                      <span className={`ml-2 font-semibold ${
                          checkedTransaction.status === 'SUCCESSFUL' ? 'text-accent-green-dark' :
                          checkedTransaction.status === 'FAILED' ? 'text-accent-red-dark' :
                          'text-yellow-600'
                      }`}>
                          {checkedTransaction.status}
                      </span>
                  </p>
              </div>
          )}
      </div>

      {/* Display Recent Transactions */}
      <div>
        <h4 className="text-md font-semibold text-neutral-700 mb-3">Recent Transactions</h4>
        {listLoading && <p className="text-center text-primary-blue my-4">Loading history...</p>}
        {!listLoading && transactions.length === 0 && (
          <p className="text-center text-neutral-500 my-4 text-sm">No recent transactions to display. (Endpoint not implemented or none found).</p>
        )}
        {!listLoading && transactions.length > 0 && (
          <div className="space-y-3">
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
                  <span className="text-neutral-600">{formatCurrency(tx.amount)}</span>
                </div>
                 <p className="text-xs text-neutral-500">To: {tx.merchant_id}</p>
                 <p className="text-xs text-neutral-400 mt-1 truncate">ID: {tx.transaction_id}</p>
                 {tx.updated_at && (
                    <p className="text-xs text-neutral-400">Updated: {new Date(tx.updated_at * 1000).toLocaleString()}</p>
                 )}
                 {pollingIntervalId.current && tx.status === 'PENDING' && tx.transaction_id === transactions[0]?.transaction_id && (
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