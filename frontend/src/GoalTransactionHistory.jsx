import React, { useState, useEffect, useCallback } from 'react'; // 1. Import useCallback
import { useWallet, formatCurrency } from './contexts/WalletContext';
import { toast } from 'react-hot-toast';

// (formatTimestamp helper - no changes)
const formatTimestamp = (timestamp) => { try { const num = typeof timestamp === 'string' ? parseInt(timestamp, 10) : timestamp; if(isNaN(num)) return '?'; return new Date(num * 1000).toLocaleDateString(); } catch(e){ return '?'; } };


function GoalTransactionHistory({ goalId }) {
  const { apiUrl, authorizedFetch } = useWallet();
  
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false); // State to toggle visibility
  const [error, setError] = useState(null); // 2. Add error state

  // 3. Wrap fetchHistory in useCallback
  const fetchHistory = useCallback(async () => {
    if (!isOpen || !authorizedFetch) return; 
    
    setLoading(true);
    setError(null); // Reset error
    try {
      const response = await authorizedFetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}/transactions`);
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || 'Failed to fetch history');
      }
      const data = await response.json();
      setTransactions(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(err.message); // Use toast, but also set local error
      setError(err.message);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }, [goalId, apiUrl, isOpen, authorizedFetch]); // Dependencies are correct

  // 4. useEffect now correctly depends on the memoized function
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  if (!goalId) return null;

  return (
    <div className="mt-4 pt-3 border-t border-neutral-200">
      {/* Button to toggle history visibility */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-xs font-semibold text-primary-blue hover:text-primary-blue-dark"
      >
        {isOpen ? 'Hide' : 'Show'} Contribution History
      </button>

      {/* Only render the list if it's open */}
      {isOpen && (
        <div className="mt-2">
          {loading && (
            <div className="flex justify-center items-center my-1">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-blue"></div>
            </div>
          )}
          {error && <p className="my-1 p-1 bg-accent-red-light border border-accent-red text-accent-red-dark rounded text-xs">{error}</p>}

          {!loading && !error && transactions.length === 0 && (
            <p className="text-center text-neutral-500 my-1 text-xs">No contributions found.</p>
          )}

          {!loading && !error && transactions.length > 0 && (
            <ul className="space-y-1 max-h-40 overflow-y-auto pr-1">
              {transactions.map((tx) => (
                <li key={tx.transaction_id} className="flex justify-between items-center p-1 bg-neutral-100/50 rounded text-xs">
                  <span className="text-neutral-500">{formatTimestamp(tx.timestamp)}</span>
                  <span className="font-medium text-accent-green-dark">
                    +{formatCurrency(tx.amount)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default GoalTransactionHistory;