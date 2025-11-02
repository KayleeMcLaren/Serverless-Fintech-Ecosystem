import React, { useState, useEffect } from 'react';
import { useWallet, formatCurrency } from './contexts/WalletContext';
import Spinner from './Spinner';
import { toast } from 'react-hot-toast';
import { BanknotesIcon, CreditCardIcon } from '@heroicons/react/24/outline';
import WalletPrompt from './WalletPrompt';

function Dashboard() {
  // Get wallet and API URL from context
  const { wallet, apiUrl, authorizedFetch } = useWallet();
  const walletId = wallet ? wallet.wallet_id : null;

  // Local state for our calculated data
  const [totalSavings, setTotalSavings] = useState(0);
  const [totalDebt, setTotalDebt] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for walletId AND authorizedFetch
    if (walletId && authorizedFetch) {
      // Fetch all data when walletId is available
      const fetchData = async () => {
        setLoading(true);
        try {
          // Fetch savings goals and approved loans in parallel
          const [savingsResponse, loansResponse] = await Promise.all([
            authorizedFetch(`${apiUrl}/savings-goal/by-wallet/${encodeURIComponent(walletId)}`),
            authorizedFetch(`${apiUrl}/loan/by-wallet/${encodeURIComponent(walletId)}`)
          ]);

          if (!savingsResponse.ok) throw new Error('Failed to fetch savings goals');
          if (!loansResponse.ok) throw new Error('Failed to fetch loans');

          const savingsData = await savingsResponse.json();
          const loansData = await loansResponse.json();

          // Calculate total savings
          const totalSaved = (Array.isArray(savingsData) ? savingsData : []).reduce((acc, goal) => {
            return acc + parseFloat(goal.current_amount || '0');
          }, 0);
          setTotalSavings(totalSaved);

          // Calculate total debt (only from 'APPROVED' loans)
          const totalOwed = (Array.isArray(loansData) ? loansData : [])
            .filter(loan => loan.status === 'APPROVED')
            .reduce((acc, loan) => {
              return acc + parseFloat(loan.remaining_balance || '0');
            }, 0);
          setTotalDebt(totalOwed);

        } catch (e) {
          toast.error(`Failed to load dashboard data: ${e.message}`);
        } finally {
          setLoading(false);
        }
      };

      fetchData();
    } else {
      // No wallet loaded, reset states
      setLoading(false);
      setTotalSavings(0);
      setTotalDebt(0);
    }
    // --- ADD authorizedFetch to the dependency array ---
  }, [walletId, apiUrl, authorizedFetch]); 

  if (loading && !walletId) {
    // Don't show loading spinner if we're just waiting for a wallet
    return <WalletPrompt />;
  }

  if (loading && walletId) {
    return (
      <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
        <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Dashboard</h2>
        <Spinner />
      </div>
    );
  }
  
  if (!walletId) {
     return <WalletPrompt />;
  }

  // Main dashboard display
  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Financial Overview</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Stat Card: Wallet Balance */}
        <div className="p-4 bg-white border border-neutral-200 rounded-lg shadow-sm">
          <h3 className="text-sm font-medium text-neutral-500">Current Balance</h3>
          <p className="mt-1 text-3xl font-semibold text-primary-blue-dark">
            {formatCurrency(wallet?.balance || 0)}
          </p>
        </div>

        {/* Stat Card: Total Savings */}
        <div className="p-4 bg-white border border-neutral-200 rounded-lg shadow-sm">
          <h3 className="text-sm font-medium text-neutral-500 flex items-center">
             <BanknotesIcon className="h-5 w-5 mr-1.5" /> Total Savings
          </h3>
          <p className="mt-1 text-3xl font-semibold text-accent-green-dark">
            {formatCurrency(totalSavings)}
          </p>
        </div>

        {/* Stat Card: Total Debt */}
        <div className="p-4 bg-white border border-neutral-200 rounded-lg shadow-sm">
          <h3 className="text-sm font-medium text-neutral-500 flex items-center">
            <CreditCardIcon className="h-5 w-5 mr-1.5" /> Total Debt
          </h3>
          <p className="mt-1 text-3xl font-semibold text-accent-red-dark">
            {formatCurrency(totalDebt)}
          </p>
        </div>

      </div>
    </div>
  );
}

export default Dashboard;