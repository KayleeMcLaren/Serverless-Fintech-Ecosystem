import React, { useState, useEffect } from 'react';

// Keep formatCurrency helper
const formatCurrency = (amount) => {
  try {
    const numberAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numberAmount)) return String(amount);
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numberAmount);
  } catch (e) {
    return String(amount);
  }
};

function SavingsGoals({ walletId, apiUrl }) {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(false); // General loading for fetch/create/delete
  const [addFundsLoading, setAddFundsLoading] = useState(null); // Track loading state per goal ID
  const [error, setError] = useState(null);
  const [newGoalName, setNewGoalName] = useState('');
  const [newGoalTarget, setNewGoalTarget] = useState('');
  const [addAmount, setAddAmount] = useState({}); // State to hold amount input for each goal { goalId: amount }

  // --- Keep useEffect, fetchGoals, handleCreateGoal, handleDeleteGoal ---
  useEffect(() => {
    if (walletId) {
      fetchGoals();
    } else {
      setGoals([]);
    }
     // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]);

  const fetchGoals = async () => {
    // ... (keep fetchGoals function the same)
    if (!walletId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/savings-goal/by-wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setGoals(data);
    } catch (e) {
      setError(`Failed to fetch savings goals: ${e.message}`);
      setGoals([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGoal = async (e) => {
    // ... (keep handleCreateGoal function the same)
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
      fetchGoals();
    } catch (e) {
      setError(`Failed to create goal: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

   const handleDeleteGoal = async (goalId) => {
     // ... (keep handleDeleteGoal function the same)
     if (!window.confirm('Are you sure you want to delete this savings goal?')) {
      return;
    }
    setLoading(true); // Use general loading here, or specific if preferred
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}`, {
        method: 'DELETE',
      });
      const responseBody = await response.json();
      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      fetchGoals();
    } catch (e) {
      setError(`Failed to delete goal: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // --- NEW: Add Funds to Goal Function ---
  const handleAddToGoal = async (goalId) => {
    const amountToAddStr = String(addAmount[goalId] || '').trim();
    if (!amountToAddStr || parseFloat(amountToAddStr) <= 0) {
      setError(`Please enter a positive amount for goal ${goalId}.`);
      return;
    }
    const amount = parseFloat(amountToAddStr).toFixed(2);

    setAddFundsLoading(goalId); // Set loading state specifically for this goal
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_id: walletId, // Pass the main wallet ID
          amount: amount,
        }),
      });
      const responseBody = await response.json();
      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      // Clear the input for this specific goal
      setAddAmount(prev => ({ ...prev, [goalId]: '' }));
      // Refetch goals to update the current amount and progress bar
      // Also refetch the main wallet balance (requires passing a function down or lifting state - TBD)
      fetchGoals();
      // TODO: Add a way to trigger wallet balance refetch in App.jsx
      console.log(`Successfully added funds to goal ${goalId}`);
    } catch (e) {
      setError(`Failed to add funds to goal ${goalId}: ${e.message}`);
    } finally {
      setAddFundsLoading(null); // Clear loading state for this goal
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
            const isLoadingThisGoal = addFundsLoading === goal.goal_id; // Check if this goal is currently processing 'add funds'

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
                     disabled={loading || isLoadingThisGoal} // Disable if any loading is happening
                     className="px-2 py-1 bg-accent-red text-white text-xs rounded hover:bg-accent-red-dark disabled:bg-neutral-300 disabled:cursor-not-allowed disabled:text-neutral-500 flex-shrink-0"
                   >
                     Delete
                   </button>
                </div>
                {/* Progress Bar */}
                <div className="w-full bg-neutral-200 rounded-full h-2.5 dark:bg-neutral-700 mt-1 mb-3"> {/* Added margin-bottom */}
                  <div
                    className="bg-primary-blue h-2.5 rounded-full transition-all duration-300 ease-out" // Added transition
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
                {/* --- End Add Funds --- */}
              </li>
            );
          })}
        </ul>
      )}

      {/* --- Form to Create New Goal --- */}
      <form onSubmit={handleCreateGoal} className="mt-6 pt-4 border-t border-neutral-200">
        {/* ... (keep create goal form the same) ... */}
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