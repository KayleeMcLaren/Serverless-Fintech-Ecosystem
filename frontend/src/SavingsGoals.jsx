import React, { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import GoalTransactionHistory from './GoalTransactionHistory';
import Spinner from './Spinner';
import { useWallet, formatCurrency } from './contexts/WalletContext';
import ConfirmModal from './ConfirmModal';
import { BanknotesIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import WalletPrompt from './WalletPrompt';

function SavingsGoals() {
  const { wallet, apiUrl, refreshWalletAndHistory, authorizedFetch } = useWallet();
  const walletId = wallet ? wallet.wallet_id : null;
  
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [newGoalName, setNewGoalName] = useState('');
  const [newGoalTarget, setNewGoalTarget] = useState('');
  const [addAmount, setAddAmount] = useState({});

  // State for Delete Modal
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [goalToDelete, setGoalToDelete] = useState(null);

  // State for Redeem Modal
  const [isRedeemModalOpen, setIsRedeemModalOpen] = useState(false);
  const [goalToRedeem, setGoalToRedeem] = useState(null);

  const newGoalNameInputRef = useRef(null);

  // --- 1. Correct fetchGoals (wrapped in useCallback) ---
  const fetchGoals = useCallback(async () => {
    if (!walletId || !authorizedFetch) {
      setGoals([]); // Clear goals if no wallet or auth
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await authorizedFetch(`${apiUrl}/savings-goal/by-wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
         let errorMsg = `HTTP error! Status: ${response.status}`;
         try { const errBody = await response.json(); errorMsg = errBody.message || errorMsg; } catch(e){}
        throw new Error(errorMsg);
      }
      const data = await response.json();
      setGoals(Array.isArray(data) ? data : []);
    } catch (e) {
      toast.error(`Fetch goals failed: ${e.message}`);
      setGoals([]);
    } finally {
      setLoading(false);
    }
  }, [walletId, apiUrl, authorizedFetch]);

  // --- 2. Correct useEffect ---
  // This is the ONLY useEffect that should call fetchGoals
  useEffect(() => {
    fetchGoals();
  }, [fetchGoals]);
  // ---

  // --- (handleCreateGoal - no changes) ---
  const handleCreateGoal = async (e) => {
    e.preventDefault();
    if (!walletId || !newGoalName || !newGoalTarget || parseFloat(newGoalTarget) <= 0) {
      toast.error('Please provide a goal name and a positive target amount.');
      return;
    }
    setLoading(true);

    await toast.promise(
      authorizedFetch(`${apiUrl}/savings-goal`, {
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
        fetchGoals();
      }),
      {
         loading: 'Adding goal...',
         success: <b>Goal created!</b>,
         error: (err) => <b>Failed to create goal: {err.message}</b>,
      }
    );
    setLoading(false);
  };

  // --- (handleAmountChange - no changes) ---
  const handleAmountChange = (goalId, value) => {
    setAddAmount(prev => ({ ...prev, [goalId]: value }));
  };

  // --- (promptDeleteGoal - no changes) ---
  const promptDeleteGoal = (goalId) => {
    setGoalToDelete(goalId);
    setIsDeleteModalOpen(true);
  };

  // --- (executeDeleteGoal - no changes) ---
  const executeDeleteGoal = async () => {
    if (!goalToDelete) return;
    const goalId = goalToDelete;
    setActionLoading(prev => ({ ...prev, [goalId]: true }));
    setIsDeleteModalOpen(false);

    await toast.promise(
        authorizedFetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalToDelete)}`, {
            method: 'DELETE',
        })
        .then(async(response) => {
            const responseBody = await response.json();
            if (!response.ok) throw new Error(responseBody?.message || `HTTP error!`);
            return responseBody;
        })
        .then(() => {
            fetchGoals(); // Refetch goals
            if (refreshWalletAndHistory) { // Refresh wallet balance
                refreshWalletAndHistory();
            }
        }),
        {
            loading: 'Deleting goal...',
            success: <b>Goal deleted!</b>,
            error: (err) => <b>Failed to delete goal: {err.message}</b>,
        }
    );
    setActionLoading(prev => ({ ...prev, [goalId]: false }));
    setGoalToDelete(null);
  };

  // --- (handleAddToGoal - cleaned up console.log) ---
  const handleAddToGoal = async (goalId) => {
    const amountToAddStr = String(addAmount[goalId] || '').trim();
    if (!amountToAddStr || parseFloat(amountToAddStr) <= 0) {
      toast.error(`Please enter a positive amount.`);
      return;
    }
    const amount = parseFloat(amountToAddStr).toFixed(2);

    setActionLoading(prev => ({ ...prev, [goalId]: true }));

    await toast.promise(
        authorizedFetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalId)}/add`, {
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
            fetchGoals();
            if (refreshWalletAndHistory) {
                refreshWalletAndHistory();
            }
        }),
        {
            loading: 'Adding funds...',
            success: <b>Funds added!</b>,
            error: (err) => <b>Failed to add funds: {err.message}</b>,
        }
    );
    setActionLoading(prev => ({ ...prev, [goalId]: false }));
  };

  
  // --- (Redeem Goal functions - no changes) ---
  const promptRedeemGoal = (goal) => {
    setGoalToRedeem(goal);
    setIsRedeemModalOpen(true);
  };

  const executeRedeemGoal = async () => {
    if (!goalToRedeem) return;
    const goalId = goalToRedeem.goal_id;
    setActionLoading(prev => ({ ...prev, [goalId]: true }));
    setIsRedeemModalOpen(false);

    await toast.promise(
        authorizedFetch(`${apiUrl}/savings-goal/${encodeURIComponent(goalToRedeem.goal_id)}/redeem`, {
            method: 'POST',
        })
        .then(async(response) => {
            const responseBody = await response.json();
            if (!response.ok) {
                throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
            }
            return responseBody;
        })
        .then(() => {
            fetchGoals();
            if (refreshWalletAndHistory) {
                refreshWalletAndHistory();
            }
        }),
        {
            loading: 'Redeeming goal...',
            success: <b>Goal redeemed! Funds are in your wallet.</b>,
            error: (err) => <b>Failed to redeem: {err.message}</b>,
        }
    );
    setActionLoading(prev => ({ ...prev, [goalId]: false }));
    setGoalToRedeem(null);
  };


  // --- Render Logic ---
  if (!walletId) {
    return <WalletPrompt />;
  }

  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Savings Goals</h2>

      {loading && <Spinner />}

      {!loading && goals.length === 0 && (
        <div className="text-center text-neutral-500 my-4 py-8">
          <BanknotesIcon className="h-12 w-12 mx-auto text-neutral-400" />
          <h3 className="mt-2 text-sm font-semibold text-neutral-700">No Savings Goals</h3>
          <p className="mt-1 text-sm text-neutral-500">Get started by adding a new goal below.</p>
        </div>
      )}

      {!loading && goals.length > 0 && (
        <ul className="space-y-4 mb-6">
          {goals.map((goal) => {
            const current = parseFloat(goal.current_amount || '0');
            const target = parseFloat(goal.target_amount);
            const percentage = target > 0 ? Math.min((current / target) * 100, 100) : 0;
            const isLoadingThisGoalAction = actionLoading[goal.goal_id];
            const isComplete = percentage >= 100;

            return (
              <li key={goal.goal_id} className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <span className="font-medium text-neutral-800">{goal.goal_name}</span>
                    <span className="block text-sm text-neutral-600">
                      {formatCurrency(current)} / {formatCurrency(target)}
                      <span className="ml-2 text-xs font-semibold text-primary-blue">({percentage.toFixed(0)}%)</span>
                    </span>
                  </div>
                   <button
                     onClick={() => promptDeleteGoal(goal.goal_id)}
                     disabled={loading || isLoadingThisGoalAction}
                     className="px-2 py-1 bg-accent-red text-white text-xs rounded hover:bg-accent-red-dark disabled:bg-neutral-300 disabled:cursor-not-allowed disabled:text-neutral-500 flex-shrink-0"
                   >
                     {/* --- 3. FIX: Check object key --- */}
                     {actionLoading[goal.goal_id] ? '...' : 'Delete'}
                   </button>
                </div>
               
                <div className="w-full bg-neutral-200 rounded-full h-2.5 dark:bg-neutral-700 mt-1 mb-3">
                  <div
                    // --- Always blue ---
                    className={`h-2.5 rounded-full transition-all duration-300 ease-out bg-primary-blue`}
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>

                {!isComplete ? (
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
                ) : (
                  <div className="mt-2">
                    <button
                      onClick={() => promptRedeemGoal(goal)}
                      disabled={loading || isLoadingThisGoalAction}
                      className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-accent-green text-white text-sm font-semibold rounded hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-1 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                    >
                      <CheckCircleIcon className="h-5 w-5" />
                      {isLoadingThisGoalAction ? 'Redeeming...' : 'Redeem Goal'}
                    </button>
                  </div>
                )}
                 
                 <GoalTransactionHistory goalId={goal.goal_id} />
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
            ref={newGoalNameInputRef}
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
      
      {/* --- Delete Modal --- */}
      <ConfirmModal
        isOpen={isDeleteModalOpen}
        title="Confirm Deletion"
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={executeDeleteGoal}
        confirmText="Delete"
        confirmVariant="danger"
      >
        Are you sure you want to delete this savings goal? Any funds will be returned to your wallet.
      </ConfirmModal>

      {/* --- Redeem Modal --- */}
      <ConfirmModal
        isOpen={isRedeemModalOpen}
        title="Confirm Redemption"
        onClose={() => setIsRedeemModalOpen(false)}
        onConfirm={executeRedeemGoal}
        confirmText="Redeem"
        confirmVariant="primary"
      >
        Are you sure you want to redeem this goal? The total amount of <b>{formatCurrency(goalToRedeem?.current_amount)}</b> will be transferred to your main wallet and this goal will be deleted.
      </ConfirmModal>
    </div>
  );
}

export default SavingsGoals;