import React, { useState, useEffect } from 'react';

// --- DEFINE formatCurrency HERE ---
const formatCurrency = (amount) => {
  try {
    // Attempt to convert to number if it's a string representation from DynamoDB
    const numberAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    // Check if the conversion resulted in NaN (Not a Number)
    if (isNaN(numberAmount)) return String(amount); // Return original string if invalid
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numberAmount);
  } catch (e) {
    console.error("Error formatting currency:", amount, e);
    return String(amount); // Fallback to original string representation
  }
};
// --- END formatCurrency ---

// Helper to format timestamp
const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
        // Ensure timestamp is a number before multiplying
        const numericTimestamp = typeof timestamp === 'string' ? parseInt(timestamp, 10) : timestamp;
        if (isNaN(numericTimestamp)) return 'Invalid Date';
        return new Date(numericTimestamp * 1000).toLocaleString(); // Convert seconds to milliseconds
    } catch (e) {
        console.error("Error formatting timestamp:", timestamp, e);
        return 'Invalid Date';
    }
};

function TransactionHistory({ walletId, apiUrl }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (walletId) {
      fetchHistory();
    } else {
      setTransactions([]);
    }
     // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]);

  const fetchHistory = async () => {
    if (!walletId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/wallet/${encodeURIComponent(walletId)}/transactions?limit=20`); // Fetch last 20
      if (!response.ok) {
        // Try parsing error response from API
        let errorMsg = `HTTP error! Status: ${response.status}`;
        try {
            const errBody = await response.json();
            errorMsg = errBody.message || errorMsg;
        } catch(parseErr) {
            // Ignore if error response isn't JSON
        }
        throw new Error(errorMsg);
      }
      const data = await response.json();
      // Ensure data is an array before setting state
      setTransactions(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(`Failed to fetch transaction history: ${e.message}`);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  // Function to determine text color based on transaction type
  const getAmountColor = (type) => {
    if (type === 'CREDIT' || type === 'LOAN_IN') return 'text-accent-green-dark';
    if (type === 'DEBIT' || type === 'PAYMENT_OUT') return 'text-accent-red-dark';
    return 'text-neutral-700';
  };

  // Function to get a user-friendly description
  const getDescription = (tx) => {
    // Get potential names from details, provide fallbacks
    const merchantName = tx.details?.merchant || 'Merchant';
    const goalName = tx.details?.goal_name || 'Savings Goal'; // Look for goal_name

    switch (tx.type) {
        case 'CREDIT': return 'Deposit';
        case 'DEBIT': return 'Withdrawal';
        case 'LOAN_IN': return `Loan Funded (${(tx.related_id || 'N/A').substring(0, 8)}...)`;
        // Use merchantName from details
        case 'PAYMENT_OUT': return `Payment to ${merchantName}`;
        // Use goalName from details
        case 'SAVINGS_ADD': return `Added to ${goalName}`;
        default: return tx.type || 'Transaction'; // Fallback
    }
  };


  if (!walletId) return null; // Don't render if no wallet selected

  return (
    <div className="mt-5 pt-4 border-t border-neutral-200"> {/* Use neutral border */}
      <h4 className="text-md font-semibold text-neutral-700 mb-3">Transaction History</h4>
      {loading && <p className="text-center text-primary-blue my-2">Loading history...</p>}
      {error && <p className="my-2 p-2 bg-accent-red-light border border-accent-red text-accent-red-dark rounded-md text-sm">{error}</p>}

      {!loading && transactions.length === 0 && (
        <p className="text-center text-neutral-500 my-2 text-sm">No transactions found.</p>
      )}

      {!loading && transactions.length > 0 && (
        <ul className="space-y-2 max-h-60 overflow-y-auto pr-2"> {/* Limit height and add scroll */}
          {transactions.map((tx) => {
            // ... (keep existing amountColor, amountSign calculation) ...
            const isCredit = tx.type === 'CREDIT' || tx.type === 'LOAN_IN' || tx.type === 'SAVINGS_ADD'; // Include SAVINGS_ADD as credit type display
            const amountColor = isCredit ? 'text-accent-green-dark' : 'text-accent-red-dark';
            const amountSign = isCredit ? '+' : '-';

            // Check balance type and format
            const balance_is_goal = tx.details?.balance_is_goal === true
            const balanceLabel = balance_is_goal ? 'Goal Bal:' : 'Bal:'; // Choose label
            const balanceAfter = (tx.balance_after !== 'N/A' && tx.balance_after !== undefined)
                ? formatCurrency(tx.balance_after)
                : 'N/A';

            return (
              <li key={tx.transaction_id} className="p-2 bg-neutral-100 border border-neutral-200 rounded text-xs">
                {/* Top Row: Description and Amount */}
                <div className="flex justify-between items-center mb-1">
                  <span className="block font-medium text-neutral-700">{getDescription(tx)}</span>
                  <span className={`font-semibold ${amountColor}`}>
                    {amountSign}
                    {formatCurrency(tx.amount)}
                  </span>
                </div>
                {/* Bottom Row: Date and Appropriate Balance */}
                <div className="flex justify-between items-center text-neutral-500">
                   <span>{formatTimestamp(tx.timestamp)}</span>
                   {/* Display correct label and balance */}
                   <span>{balanceLabel} {balanceAfter}</span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
       {/* Optional: Add a button to view full history */}
    </div>
  );
}

export default TransactionHistory;