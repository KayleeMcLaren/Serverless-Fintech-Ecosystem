import React, { useState, useEffect, useCallback } from 'react'; // 1. Import useCallback
import Spinner from './Spinner';
import { ClipboardDocumentListIcon } from '@heroicons/react/24/outline';
import { useWallet, formatCurrency } from './contexts/WalletContext';

// (formatTimestamp helper - no changes)
const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
        const numericTimestamp = typeof timestamp === 'string' ? parseInt(timestamp, 10) : timestamp;
        if (isNaN(numericTimestamp)) return 'Invalid Date';
        return new Date(numericTimestamp * 1000).toLocaleString();
    } catch (e) {
        console.error("Error formatting timestamp:", timestamp, e);
        return 'Invalid Date';
    }
};

function TransactionHistory() {
  // 1. Get wallet state and functions from context
  const { wallet, apiUrl, transactionCount, authorizedFetch } = useWallet();
  const walletId = wallet ? wallet.wallet_id : null;
  
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- 2. Wrap fetchHistory in useCallback ---
  const fetchHistory = useCallback(async () => {
    if (!walletId || !authorizedFetch) {
        setTransactions([]);
        return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await authorizedFetch(`${apiUrl}/wallet/${encodeURIComponent(walletId)}/transactions?limit=20`);
      if (!response.ok) {
        let errorMsg = `HTTP error! Status: ${response.status}`;
        try { const errBody = await response.json(); errorMsg = errBody.message || errorMsg; } catch(parseErr) {}
        throw new Error(errorMsg);
      }
      const data = await response.json();
      setTransactions(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(`Failed to fetch transaction history: ${e.message}`);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }, [walletId, apiUrl, authorizedFetch]); // Dependencies for useCallback

  // --- 3. Update useEffect to depend on fetchHistory and transactionCount ---
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory, transactionCount]); // Re-fetches when wallet changes (via fetchHistory) or a transaction completes

  // (Helper functions: getAmountColor, getAmountSign, getDescription - no changes)
  const getAmountColor = (type) => {
    if (type === 'CREDIT' || type === 'LOAN_IN' || type === 'WALLET_CREATED' || type === 'SAVINGS_REFUND' || type === 'SAVINGS_REDEEM') return 'text-accent-green-dark';
    if (type === 'DEBIT' || type === 'PAYMENT_OUT' || type === 'SAVINGS_ADD') return 'text-accent-red-dark';
    return 'text-neutral-700';
  };
  
  const getAmountSign = (type) => {
    if (type === 'CREDIT' || type === 'LOAN_IN' || type === 'WALLET_CREATED' || type === 'SAVINGS_REFUND' || type === 'SAVINGS_REDEEM') return '+'; 
    if (type === 'DEBIT' || type === 'PAYMENT_OUT' || type === 'SAVINGS_ADD') return '-';
    return '';
  };
  
  const getDescription = (tx) => {
    const goalName = tx.details?.goal_name || 'Savings Goal';
    const merchantName = tx.details?.merchant || 'Merchant';
    switch (tx.type) {
      case 'WALLET_CREATED': return 'Wallet Created';
        case 'CREDIT': return 'Deposit';
        case 'DEBIT': return 'Withdrawal';
        case 'LOAN_IN': return `Loan Funded (${(tx.related_id || 'N/A').substring(0, 8)}...)`;
        case 'PAYMENT_OUT': return `Payment to ${merchantName}`;
        case 'SAVINGS_ADD': return `Added to ${goalName}`; // Simplified name
        case 'LOAN_REPAYMENT': return 'Loan Repayment';
        case 'SAVINGS_REFUND': return 'Savings Goal Refund';
        case 'SAVINGS_REDEEM': return 'Savings Goal Redeemed';
        default: return tx.type || 'Transaction';
    }
  };
  // ---

  if (!walletId) { return null; } // Don't render if no wallet selected

  return (
    <div className="mt-5 pt-4 border-t border-neutral-200">
      
      {loading && (
          <div className="scale-75">
            <Spinner />
          </div>
      )}
      
      {error && <p className="my-2 p-2 bg-accent-red-light border border-accent-red text-accent-red-dark rounded-md text-sm">{error}</p>}

      {!loading && !error && transactions.length === 0 && (
        <div className="text-center text-neutral-500 my-4 py-4">
          <ClipboardDocumentListIcon className="h-10 w-10 mx-auto text-neutral-400" />
          <p className="mt-2 text-sm text-neutral-500">No transactions found.</p>
          <p className="text-xs text-neutral-400">Make a deposit or payment to see it here.</p>
        </div>
      )}

      {!loading && !error && transactions.length > 0 && (
        <ul className="space-y-2 max-h-60 overflow-y-auto pr-2">
          {transactions.map((tx) => {
            const amountColor = getAmountColor(tx.type);
            const amountSign = getAmountSign(tx.type);
            const balance_is_goal = tx.details?.balance_is_goal === true;
            const balanceLabel = balance_is_goal ? 'Goal Bal:' : 'Bal:';
            const balanceAfter = (tx.balance_after !== 'N/A' && tx.balance_after !== undefined)
                ? formatCurrency(tx.balance_after)
                : 'N/A';

            return (
              <li key={tx.transaction_id} className="p-2 bg-neutral-100 border border-neutral-200 rounded text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="block font-medium text-neutral-700">{getDescription(tx)}</span>
                  <span className={`font-semibold ${amountColor}`}>
                    {/* Don't show amount for wallet creation */}
                    {tx.type !== 'WALLET_CREATED' && (
                        <>
                            {amountSign}
                            {formatCurrency(tx.amount)}
                        </>
                    )}
                  </span>
                </div>
                <div className="flex justify-between items-center text-neutral-500">
                   <span>{formatTimestamp(tx.timestamp)}</span>
                   <span>{balanceLabel} {balanceAfter}</span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default TransactionHistory;