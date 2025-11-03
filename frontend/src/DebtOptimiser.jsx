import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import Spinner from './Spinner';
import { useWallet, formatCurrency } from './contexts/WalletContext';
import { BanknotesIcon, ClockIcon, TrophyIcon, ArrowRightIcon } from '@heroicons/react/24/outline';
import WalletPrompt from './WalletPrompt';

function DebtOptimiser() {
  const { wallet, apiUrl, authorizedFetch } = useWallet();
  const walletId = wallet ? wallet.wallet_id : null;

  const [budget, setBudget] = useState('');
  // Results now holds the two projections (min and accel) and saved metrics
  const [results, setResults] = useState(null); 
  const [loading, setLoading] = useState(false);
  const [loansLoading, setLoansLoading] = useState(false);
  const [noLoansFound, setNoLoansFound] = useState(false);
  const [totalMinimumPayment, setTotalMinimumPayment] = useState(0);
  const [loans, setLoans] = useState([]);


  const fetchApprovedLoans = useCallback(async () => {
    if (!walletId || !authorizedFetch) return; 
    setLoansLoading(true);
    setNoLoansFound(false);
    setResults(null); 
    setBudget('');    
    try {
      const response = await authorizedFetch(`${apiUrl}/loan/by-wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || 'Failed to fetch loans');
      }
      const data = await response.json();
      const approvedLoans = Array.isArray(data) ? data.filter(loan => loan.status === 'APPROVED') : [];
      
      if (approvedLoans.length === 0) {
        setNoLoansFound(true);
      }
      setLoans(approvedLoans);
    } catch (err) {
      toast.error(err.message);
      setLoans([]);
      setNoLoansFound(true);
    } finally {
      setLoansLoading(false);
    }
  }, [walletId, apiUrl, authorizedFetch]);

  useEffect(() => {
    if (walletId && authorizedFetch) {
        fetchApprovedLoans();
    }
  }, [fetchApprovedLoans, walletId, authorizedFetch]);

  useEffect(() => {
    if (loans.length > 0) {
      const totalMin = loans.reduce((acc, loan) => {
        return acc + parseFloat(loan.minimum_payment || '0');
      }, 0);
      setTotalMinimumPayment(totalMin);
    } else {
      setTotalMinimumPayment(0);
    }
  }, [loans]);
  
  // No chartData useEffect needed now, as the line chart is gone.

  // --- Calculate Handler (Uses simplified backend logic) ---
  const handleCalculate = async (e) => {
    e.preventDefault();
    const extra = parseFloat(budget || '0');
    if (!walletId || extra < 0) {
      toast.error('Please enter a valid extra payment amount (0 or more).');
      return;
    }
    
    const totalBudget = totalMinimumPayment + extra;
    
    setLoading(true);
    setResults(null);
    const calculationToastId = toast.loading('Calculating payoff projections...');

    try {
      const response = await authorizedFetch(`${apiUrl}/debt-optimiser`, {
        method: 'POST',
        body: JSON.stringify({
          wallet_id: walletId,
          monthly_budget: totalBudget.toFixed(2),
        }),
      });
      
      const responseBody = await response.json();

      if (!response.ok) {
        if (response.status === 400 && responseBody.total_minimum_payment) {
          const minPayment = formatCurrency(responseBody.total_minimum_payment);
          throw new Error(`Budget is too low. Total minimum payment is ${minPayment}.`);
        }
        else {
          throw new Error(responseBody.message || `HTTP error! Status: ${response.status}`);
        }
      } else {
        setResults(responseBody);
        toast.success(<b>Projections calculated!</b>, { id: calculationToastId });
      }
    } catch (error) {
      console.error("Calculation failed:", error);
      toast.error(<b>{error.message}</b>, { id: calculationToastId });
    } finally {
      setLoading(false);
    }
  };


  // --- Render Logic ---
  if (!walletId) { 
    return <WalletPrompt />;
  }
  if (loansLoading) {
    return (
        <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
            <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Projection</h2>
            <Spinner />
        </div>
    );
  }
  if (noLoansFound) {
      return (
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
              <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Projection</h2>
              <div className="text-center text-neutral-500 my-4 py-8">
                  <BanknotesIcon className="h-12 w-12 mx-auto text-neutral-400" />
                  <h3 className="mt-2 text-sm font-semibold text-neutral-700">No Approved Loans Found</h3>
                  <p className="mt-1 text-sm text-neutral-500">You need approved loans to use the optimiser.</p>
                  <p className="mt-1 text-sm text-neutral-500">Visit the 'Loans' tab to apply for a loan.</p>
              </div>
          </div>
      );
  }

  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Projection</h2>
      
      <p className="text-sm text-neutral-600 mb-6 text-center max-w-xl mx-auto">
        This tool compares your minimum payment timeline against an <b>accelerated payoff</b> plan using your extra monthly budget.
      </p>

      {/* --- Input Form (no changes) --- */}
      <form onSubmit={handleCalculate} className="mb-6 pb-4 border-b border-neutral-200">
        
        <div className="p-3 bg-white border border-neutral-200 rounded-md shadow-sm text-center mb-4">
            <p className="text-sm text-neutral-600">Your total minimum payment is:</p>
            <p className="text-2xl font-bold text-primary-blue-dark">{formatCurrency(totalMinimumPayment)}<span className="text-base font-normal"> / mo</span></p>
        </div>

        <h4 className="text-md font-semibold text-neutral-700 mb-3">Add Extra Payment</h4>
        <div className="flex flex-wrap gap-3 mb-3 items-stretch">
          <input
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="Extra Payment ($)"
            disabled={loading}
            min="0" step="0.01"
            className="flex-grow basis-40 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 w-32 bg-teal-500 text-white rounded-md hover:bg-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:bg-teal-300 flex-shrink-0"
          >
            {loading ? <Spinner mini={true} /> : 'Calculate Plan'}
          </button>
        </div>
      </form>
      
      {loading && !results && ( <Spinner /> )}

      {/* --- Display Results --- */}
      {results && !loading && (
        <div className="mt-6">
           <h3 className="text-lg font-semibold text-neutral-800 mb-4 text-center">Payoff Comparison</h3>
            
            {/* Key Metrics Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                
                {/* Card 1: Total Interest Saved */}
                <div className="p-4 bg-white border border-neutral-200 rounded-lg shadow-sm text-center">
                    <h3 className="text-sm font-medium text-neutral-500">Interest Saved</h3>
                    <p className="mt-1 text-2xl font-bold text-accent-green-dark">
                        {formatCurrency(results.interest_saved)}
                    </p>
                </div>
                
                {/* Card 2: Total Months Saved */}
                <div className="p-4 bg-white border border-neutral-200 rounded-lg shadow-sm text-center">
                    <h3 className="text-sm font-medium text-neutral-500">Time Saved</h3>
                    <p className="mt-1 text-2xl font-bold text-accent-green-dark">
                        {Math.max(0, results.months_saved)} Months
                    </p>
                </div>
                
                 {/* Card 3: Total Principal */}
                <div className="p-4 bg-white border border-neutral-200 rounded-lg shadow-sm text-center">
                    <h3 className="text-sm font-medium text-neutral-500">Total Principal</h3>
                    <p className="mt-1 text-2xl font-bold text-primary-blue-dark">
                        {formatCurrency(results.summary.total_balance)}
                    </p>
                </div>
            </div>

            {/* --- Comparison Table / Timeline --- */}
            <div className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                <h4 className="font-semibold text-neutral-800 mb-4 text-center">Payoff Timeline</h4>
                
                <div className="grid grid-cols-3 gap-3 font-semibold text-neutral-700 border-b border-neutral-300 pb-2 mb-2">
                    <span>Plan</span>
                    <span className="text-center">Time (Months)</span>
                    <span className="text-right">Total Interest</span>
                </div>
                
                {/* Minimum Payment Plan */}
                <div className="grid grid-cols-3 gap-3 py-2 border-b border-neutral-100">
                    <span className="text-sm flex items-center text-neutral-600">
                        <ClockIcon className="h-5 w-5 mr-2 text-neutral-500" /> Minimum Payment
                    </span>
                    <span className="text-center text-sm font-medium text-neutral-700">
                        {results.projection_min.months} mo
                    </span>
                    <span className="text-right text-sm font-medium text-neutral-700">
                        {formatCurrency(results.projection_min.interest_paid)}
                    </span>
                </div>

                 {/* Accelerated Plan */}
                <div className="grid grid-cols-3 gap-3 py-2 bg-accent-green-light/30 rounded-md">
                    <span className="text-sm flex items-center font-semibold text-accent-green-dark">
                        <ArrowRightIcon className="h-5 w-5 mr-2" /> Accelerated Plan
                    </span>
                    <span className="text-center text-sm font-semibold text-accent-green-dark">
                        {results.projection_accel.months} mo
                    </span>
                    <span className="text-right text-sm font-semibold text-accent-green-dark">
                        {formatCurrency(results.projection_accel.interest_paid)}
                    </span>
                </div>
            </div>
        </div>
      )}
    </div>
  );
}

export default DebtOptimiser;