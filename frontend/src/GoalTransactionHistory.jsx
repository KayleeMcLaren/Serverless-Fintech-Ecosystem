import React, { useState, useEffect } from 'react';

const formatCurrency = (amount) => { try { const num = typeof amount === 'string' ? parseFloat(amount) : amount; if(isNaN(num)) return '?'; return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num); } catch(e){ return '?';} };
const formatTimestamp = (timestamp) => { try { const num = typeof timestamp === 'string' ? parseInt(timestamp, 10) : timestamp; if(isNaN(num)) return '?'; return new Date(num * 1000).toLocaleDateString(); } catch(e){ return '?'; } };


function GoalTransactionHistory({ goalId, apiUrl }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (goalId) {
      fetchGoalHistory();
    } else {
      setTransactions([]);
    }
     // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goalId]); // Refetch if goalId changes (shouldn't happen often here)

  const fetchGoalHistory = async () => {
    if (!goalId) return;
    setLoading(true);
    setError(null);
    try {
      // Call the new endpoint
      const response = await fetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}/transactions?limit=10`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setTransactions(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(`Failed to fetch goal history: ${e.message}`);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  if (!goalId) return null;

  return (
    <div className="mt-4 pt-3 border-t border-neutral-200">
      <h5 className="text-xs font-semibold text-neutral-600 mb-2">Contribution History</h5>
      {loading && <p className="text-center text-primary-blue my-1 text-xs">Loading history...</p>}
      {error && <p className="my-1 p-1 bg-accent-red-light border border-accent-red text-accent-red-dark rounded text-xs">{error}</p>}

      {!loading && transactions.length === 0 && (
        <p className="text-center text-neutral-500 my-1 text-xs">No contributions found.</p>
      )}

      {!loading && transactions.length > 0 && (
        <ul className="space-y-1 max-h-40 overflow-y-auto pr-1"> {/* Smaller height/padding */}
          {transactions.map((tx) => (
            // Simplified display for goal history
            <li key={tx.transaction_id} className="flex justify-between items-center p-1 bg-neutral-100/50 rounded text-xs">
              <span className="text-neutral-500">{formatTimestamp(tx.timestamp)}</span>
              <span className="font-medium text-accent-green-dark"> {/* Assume always positive */}
                +{formatCurrency(tx.amount)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default GoalTransactionHistory;