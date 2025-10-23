import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast'; // Import toast
import GoalTransactionHistory from './GoalTransactionHistory';
import Spinner from './Spinner';

// --- formatCurrency Helper ---
const formatCurrency = (amount) => {
  try {
    const numberAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numberAmount)) return String(amount);
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numberAmount);
  } catch (e) {
    console.error("Error formatting currency:", amount, e);
    return String(amount);
  }
};
// --- End formatCurrency ---

function SavingsGoals({ walletId, apiUrl, onGoalFunded }) {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(false); // General loading for fetch/create
  const [actionLoading, setActionLoading] = useState({}); // Track loading state per goal ID for delete/add { goalId: boolean }
  // const [error, setError] = useState(null); // Replaced by toasts
  const [newGoalName, setNewGoalName] = useState('');
  const [newGoalTarget, setNewGoalTarget] = useState('');
  const [addAmount, setAddAmount] = useState({});

  // --- Fetch goals ---
  useEffect(() => {
    if (walletId) {
      fetchGoals();
    } else {
      setGoals([]);
    }
     // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]);

  const fetchGoals = async () => {
    if (!walletId) return;
    setLoading(true);
    // setError(null); // Replaced by toasts
    try {
      const response = await fetch(`${apiUrl}/savings-goal/by-wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
         let errorMsg = `HTTP error! Status: ${response.status}`;
         try { const errBody = await response.json(); errorMsg = errBody.message || errorMsg; } catch(e){}
        throw new Error(errorMsg);
      }
      const data = await response.json();
      setGoals(Array.isArray(data) ? data : []);
    } catch (e) {
      toast.error(`Fetch goals failed: ${e.message}`); // Use toast
      setGoals([]);
    } finally {
      setLoading(false);
    }
  };

  // --- Create Goal ---
  const handleCreateGoal = async (e) => {
    e.preventDefault();
    if (!walletId || !newGoalName || !newGoalTarget || parseFloat(newGoalTarget) <= 0) {
      toast.error('Please provide a goal name and a positive target amount.'); // Use toast
      return;
    }
    setLoading(true);

    await toast.promise(
      fetch(`${apiUrl}/savings-goal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_id: walletId,
          goal_name: newGoalName,
          target_amount: parseFloat(newGoalTarget).toFixed(2),
        }),
      })
      .then(async (response) => {
        const responseBody = await response.json();
        if (!response.ok) {
          throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
        }
        return responseBody;
      })
      .then(() => {
        setNewGoalName('');
        setNewGoalTarget('');
        fetchGoals(); // Refetch goals after creating
      }),
      {
         loading: 'Adding goal...',
         success: <b>Goal created!</b>,
         error: (err) => <b>Failed to create goal: {err.message}</b>,
      }
    );
    setLoading(false);
  };

  // --- Delete Goal ---
  const handleDeleteGoal = async (goalId) => {
     if (!window.confirm('Are you sure you want to delete this savings goal?')) {
      return;
    }
    setActionLoading(prev => ({ ...prev, [goalId]: true })); // Set loading for this specific goal

    await toast.promise(
        fetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}`, {
            method: 'DELETE',
        })
        .then(async(response) => {
            const responseBody = await response.json();
            if (!response.ok) {
                throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
            }
            return responseBody;
        })
        .then(() => {
            fetchGoals(); // Refetch goals after deleting
        }),
        {
            loading: 'Deleting goal...',
            success: <b>Goal deleted!</b>,
            error: (err) => <b>Failed to delete goal: {err.message}</b>,
        }
    );
    setActionLoading(prev => ({ ...prev, [goalId]: false })); // Clear loading for this goal
  };

  // --- Add Funds to Goal ---
  const handleAddToGoal = async (goalId) => {
    const amountToAddStr = String(addAmount[goalId] || '').trim();
    if (!amountToAddStr || parseFloat(amountToAddStr) <= 0) {
      toast.error(`Please enter a positive amount.`); // Use toast
      return;
    }
    const amount = parseFloat(amountToAddStr).toFixed(2);

    setActionLoading(prev => ({ ...prev, [goalId]: true })); // Set loading for this goal

    await toast.promise(
        fetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              wallet_id: walletId,
              amount: amount,
            }),
        })
        .then(async(response) => {
            const responseBody = await response.json();
            if (!response.ok) {
                throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
            }
            return responseBody;
        })
        .then(() => {
            setAddAmount(prev => ({ ...prev, [goalId]: '' }));
            fetchGoals(); // Refetch goals
            if (onGoalFunded) {
                onGoalFunded(); // Trigger parent refresh
            }
            console.log(`Successfully added funds to goal ${goalId}, triggered parent refresh.`);
        }),
        {
            loading: 'Adding funds...',
            success: <b>Funds added!</b>,
            error: (err) => <b>Failed to add funds: {err.message}</b>,
        }
    );
    setActionLoading(prev => ({ ...prev, [goalId]: false })); // Clear loading for this goal
  };

  // Helper to update amount state for a specific goal
  const handleAmountChange = (goalId, value) => {
    setAddAmount(prev => ({ ...prev, [goalId]: value }));
  };

  // --- Render Logic ---
  if (!walletId) {
    return (
      <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4 mt-6 shadow-sm text-neutral-600">
        <p>Please fetch or create a wallet first to manage savings goals.</p>
      </div>
    );
  }

  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Savings Goals</h2>

      {loading && <Spinner />}
      {/* Remove general error display if using toasts exclusively */}
      {/* {error && <p className="my-4 p-3 bg-accent-red-light ...">{error}</p>} */}

      {!loading && goals.length === 0 && (
        <p className="text-center text-neutral-500 my-4">No savings goals found for this wallet.</p>
      )}
      {!loading && goals.length > 0 && (
        <ul className="space-y-4 mb-6">
          {goals.map((goal) => {
            const current = parseFloat(goal.current_amount || '0');
            const target = parseFloat(goal.target_amount);
            const percentage = target > 0 ? Math.min((current / target) * 100, 100) : 0;
            const isLoadingThisGoalAction = actionLoading[goal.goal_id]; // Check loading state for this goal's actions

            return (
              <li key={goal.goal_id} className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                {/* Goal Name, Amounts, Delete Button */}
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <span className="font-medium text-neutral-800">{goal.goal_name}</span>
                    <span className="block text-sm text-neutral-600">
                      {formatCurrency(current)} / {formatCurrency(target)}
                      <span className="ml-2 text-xs font-semibold text-primary-blue">({percentage.toFixed(0)}%)</span>
                    </span>
                  </div>
                   <button
                     onClick={() => handleDeleteGoal(goal.goal_id)}
                     disabled={loading || isLoadingThisGoalAction} // Disable if general or specific action loading
                     className="px-2 py-1 bg-accent-red text-white text-xs rounded hover:bg-accent-red-dark disabled:bg-neutral-300 disabled:cursor-not-allowed disabled:text-neutral-500 flex-shrink-0"
                   >
                    {isLoadingThisGoalAction ? '...' : 'Delete'}
                   </button>
                </div>
                {/* Progress Bar */}
                <div className="w-full bg-neutral-200 rounded-full h-2.5 dark:bg-neutral-700 mt-1 mb-3">
                  <div
                    className="bg-primary-blue h-2.5 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>

                {/* --- Add Funds Input Group --- */}
                <div className="flex flex-wrap gap-2 items-center mt-2">
                    <input
                        type="number"
                        placeholder="Amount"
                        min="0.01"
                        step="0.01"
                        value={addAmount[goal.goal_id] || ''}
                        onChange={(e) => handleAmountChange(goal.goal_id, e.target.value)}
                        disabled={loading || isLoadingThisGoalAction}
                        className="flex-grow basis-28 p-1.5 border border-neutral-300 rounded-md text-sm focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
                    />
                    <button
                        onClick={() => handleAddToGoal(goal.goal_id)}
                        disabled={loading || isLoadingThisGoalAction || !(addAmount[goal.goal_id] > 0)}
                        className="px-3 py-1.5 bg-accent-green text-white text-xs rounded hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-1 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                    >
                        {isLoadingThisGoalAction ? 'Adding...' : 'Add Funds'}
                    </button>
                </div>
                 {/* --- Goal Transaction History --- */}
                 <GoalTransactionHistory goalId={goal.goal_id} apiUrl={apiUrl} />
              </li>
            );
          })}
        </ul>
      )}

      {/* --- Form to Create New Goal --- */}
      <form onSubmit={handleCreateGoal} className="mt-6 pt-4 border-t border-neutral-200">
         <h4 className="text-md font-semibold text-neutral-700 mb-3">Add New Goal</h4>
        <div className="flex flex-wrap gap-3 mb-3 items-stretch">
          <input /* Goal Name Input */ />
          <input /* Target Amount Input */ />
        </div>
        <div className="text-center">
          <button type="submit" /* Add Goal Button */ >
            {loading ? 'Adding...' : 'Add Goal'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default SavingsGoals;