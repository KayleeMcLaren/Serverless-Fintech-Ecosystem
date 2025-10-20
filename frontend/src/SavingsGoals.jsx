import React, { useState, useEffect } from 'react';

function SavingsGoals({ walletId, apiUrl }) {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newGoalName, setNewGoalName] = useState('');
  const [newGoalTarget, setNewGoalTarget] = useState('');

  // --- Fetch goals when walletId changes ---
  useEffect(() => {
    if (walletId) {
      fetchGoals();
    } else {
      setGoals([]); // Clear goals if no wallet ID
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]); // Dependency array includes walletId

  // --- Fetch Goals Function ---
  const fetchGoals = async () => {
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
      setGoals([]); // Clear goals on error
    } finally {
      setLoading(false);
    }
  };

  // --- Create Goal Function ---
  const handleCreateGoal = async (e) => {
    e.preventDefault(); // Prevent default form submission
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
          target_amount: parseFloat(newGoalTarget).toFixed(2), // Send as string
        }),
      });
      const responseBody = await response.json();
      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      // Add the new goal to the list immediately (optimistic update)
      // Or refetch all goals for consistency:
      setNewGoalName('');
      setNewGoalTarget('');
      fetchGoals(); // Refetch goals to get the updated list
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
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}`, {
        method: 'DELETE',
      });
      const responseBody = await response.json();
      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      // Remove the goal from the list (optimistic update)
      // Or refetch for consistency:
      fetchGoals(); // Refetch goals
    } catch (e) {
      setError(`Failed to delete goal: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };


  // --- Render Logic ---
  if (!walletId) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-6 shadow-sm text-yellow-700">
        <p>Please fetch or create a wallet first to manage savings goals.</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-gray-700 mb-6 text-center">Savings Goals</h2>

      {/* --- Loading and Error Display --- */}
      {loading && <p className="text-center text-blue-600 my-4">Loading goals...</p>}
      {error && (
        <p className="my-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm text-left">
          {error}
        </p>
      )}

      {/* --- Display Existing Goals --- */}
      {!loading && goals.length === 0 && (
        <p className="text-center text-gray-500 my-4">No savings goals found for this wallet.</p>
      )}
      {!loading && goals.length > 0 && (
        <ul className="space-y-3 mb-6">
          {goals.map((goal) => (
            <li key={goal.goal_id} className="flex justify-between items-center p-3 bg-white border border-gray-200 rounded-md shadow-sm">
              <div>
                <span className="font-medium text-gray-800">{goal.goal_name}</span>
                <span className="ml-2 text-sm text-gray-600">
                  (${goal.current_amount || '0.00'} / ${goal.target_amount})
                </span>
                {/* Add a progress bar later */}
              </div>
              <button
                onClick={() => handleDeleteGoal(goal.goal_id)}
                disabled={loading}
                className="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 disabled:bg-red-300"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* --- Form to Create New Goal --- */}
      <form onSubmit={handleCreateGoal} className="mt-6 pt-4 border-t border-gray-200">
        <h4 className="text-md font-semibold text-gray-700 mb-3">Add New Goal</h4>
        <div className="flex flex-wrap gap-3 mb-3 items-stretch">
          <input
            type="text"
            value={newGoalName}
            onChange={(e) => setNewGoalName(e.target.value)}
            placeholder="Goal Name (e.g., Vacation Fund)"
            disabled={loading}
            className="flex-grow basis-40 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 min-w-[120px]"
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
            className="flex-grow basis-32 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 min-w-[100px]"
            required
          />
        </div>
        <div className="text-center">
          <button
            type="submit"
            disabled={loading || !newGoalName || !newGoalTarget}
            className="px-4 py-2 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:bg-indigo-300"
          >
            {loading ? 'Adding...' : 'Add Goal'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default SavingsGoals;