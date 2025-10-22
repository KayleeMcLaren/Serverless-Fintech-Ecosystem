import React, { useState, useEffect } from 'react';

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
  const [loading, setLoading] = useState(false);
  const [addFundsLoading, setAddFundsLoading] = useState(null);
  const [error, setError] = useState(null);
  const [newGoalName, setNewGoalName] = useState('');
  const [newGoalTarget, setNewGoalTarget] = useState('');
  const [addAmount, setAddAmount] = useState({});

  // --- Fetch goals when walletId changes ---
  useEffect(() => {
    // Check if walletId is present before fetching
    if (walletId) {
      console.log("SavingsGoals: walletId received, fetching goals.", walletId);
      fetchGoals();
    } else {
       console.log("SavingsGoals: No walletId, clearing goals.");
      setGoals([]); // Clear goals if no wallet ID is provided
    }
    // Dependency array ensures this runs when walletId changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]);

  // --- Fetch Goals Function ---
  const fetchGoals = async () => {
    if (!walletId) {
        console.log("fetchGoals: Aborted, no walletId.");
        return;
    }
    console.log(`fetchGoals: Fetching for wallet ${walletId}...`);
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/savings-goal/by-wallet/${encodeURIComponent(walletId)}`);
      console.log(`fetchGoals: Response status ${response.status}`);
      if (!response.ok) {
        let errorMsg = `HTTP error! Status: ${response.status}`;
         try { const errBody = await response.json(); errorMsg = errBody.message || errorMsg; } catch(e){}
        throw new Error(errorMsg);
      }
      const data = await response.json();
      console.log("fetchGoals: Received data:", data);
      // Ensure data is an array before setting
      setGoals(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error("fetchGoals: Error caught:", e);
      setError(`Failed to fetch savings goals: ${e.message}`);
      setGoals([]); // Clear goals on error
    } finally {
      setLoading(false);
      console.log("fetchGoals: Fetch complete.");
    }
  };

  // --- Create Goal Function ---
  const handleCreateGoal = async (e) => {
    e.preventDefault();
    if (!walletId || !newGoalName || !newGoalTarget || parseFloat(newGoalTarget) <= 0) {
      setError('Please provide a goal name and a positive target amount.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/savings-goal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_id: walletId,
          goal_name: newGoalName,
          target_amount: parseFloat(newGoalTarget).toFixed(2),
        }),
      });
      const responseBody = await response.json();
      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      setNewGoalName('');
      setNewGoalTarget('');
      fetchGoals(); // Refetch goals after creating
    } catch (e) {
      setError(`Failed to create goal: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // --- Delete Goal Function ---
  const handleDeleteGoal = async (goalId) => {
     if (!window.confirm('Are you sure you want to delete this savings goal?')) {
      return;
    }
    setLoading(true); // Can use general loading or a specific one
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}`, {
        method: 'DELETE',
      });
      const responseBody = await response.json();
      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      fetchGoals(); // Refetch goals after deleting
    } catch (e) {
      setError(`Failed to delete goal: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // --- Add Funds to Goal Function ---
  const handleAddToGoal = async (goalId) => {
    const amountToAddStr = String(addAmount[goalId] || '').trim();
    if (!amountToAddStr || parseFloat(amountToAddStr) <= 0) {
      setError(`Please enter a positive amount for goal ${goalId}.`);
      return;
    }
    const amount = parseFloat(amountToAddStr).toFixed(2);

    setAddFundsLoading(goalId);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_id: walletId,
          amount: amount,
        }),
      });
      const responseBody = await response.json();
      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      setAddAmount(prev => ({ ...prev, [goalId]: '' }));
      fetchGoals(); // Refetch goals

      if (onGoalFunded) {
          onGoalFunded(); // Trigger wallet balance refresh in parent
      }
      console.log(`Successfully added funds to goal ${goalId}, triggered parent refresh.`);
    } catch (e) {
      setError(`Failed to add funds to goal ${goalId}: ${e.message}`);
    } finally {
      setAddFundsLoading(null);
    }
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

  // --- Keep the rest of the return(...) JSX the same ---
  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Savings Goals</h2>

      {loading && <p className="text-center text-primary-blue my-4">Loading goals...</p>}
      {error && (
        <p className="my-4 p-3 bg-accent-red-light border border-accent-red text-accent-red-dark rounded-md text-sm text-left">
          {error}
        </p>
      )}

      {!loading && goals.length === 0 && (
        <p className="text-center text-neutral-500 my-4">No savings goals found for this wallet.</p>
      )}
      {!loading && goals.length > 0 && (
        <ul className="space-y-4 mb-6">
          {goals.map((goal) => {
            const current = parseFloat(goal.current_amount || '0');
            const target = parseFloat(goal.target_amount);
            const percentage = target > 0 ? Math.min((current / target) * 100, 100) : 0;
            const isLoadingThisGoal = addFundsLoading === goal.goal_id;

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
                     disabled={loading || isLoadingThisGoal}
                     className="px-2 py-1 bg-accent-red text-white text-xs rounded hover:bg-accent-red-dark disabled:bg-neutral-300 disabled:cursor-not-allowed disabled:text-neutral-500 flex-shrink-0"
                   >
                     Delete
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
                        disabled={loading || isLoadingThisGoal}
                        className="flex-grow basis-28 p-1.5 border border-neutral-300 rounded-md text-sm focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
                    />
                    <button
                        onClick={() => handleAddToGoal(goal.goal_id)}
                        disabled={loading || isLoadingThisGoal || !(addAmount[goal.goal_id] > 0)}
                        className="px-3 py-1.5 bg-accent-green text-white text-xs rounded hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-1 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                    >
                        {isLoadingThisGoal ? 'Adding...' : 'Add Funds'}
                    </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* --- Form to Create New Goal --- */}
      <form onSubmit={handleCreateGoal} className="mt-6 pt-4 border-t border-neutral-200">
         <h4 className="text-md font-semibold text-neutral-700 mb-3">Add New Goal</h4>
        <div className="flex flex-wrap gap-3 mb-3 items-stretch">
          <input
            type="text"
            value={newGoalName}
            onChange={(e) => setNewGoalName(e.target.value)}
            placeholder="Goal Name (e.g., Vacation)"
            disabled={loading}
            className="flex-grow basis-40 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[120px]"
            required
          />
          <input
            type="number"
            value={newGoalTarget}
            onChange={(e) => setNewGoalTarget(e.target.value)}
            placeholder="Target Amount ($)"
            disabled={loading}
            min="0.01"
            step="0.01"
            className="flex-grow basis-32 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[100px]"
            required
          />
        </div>
        <div className="text-center">
          <button
            type="submit"
            disabled={loading || !newGoalName || !newGoalTarget}
            className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed"
          >
            {loading ? 'Adding...' : 'Add Goal'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default SavingsGoals;