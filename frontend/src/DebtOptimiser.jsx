import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import Spinner from './Spinner';
// --- Import Recharts Components ---
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { useWallet, formatCurrency } from './contexts/WalletContext';
import { BanknotesIcon } from '@heroicons/react/24/outline'; // Icon for empty state


// --- Custom Tooltip for Charts ---
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0];
    const isTime = data.dataKey === 'Payoff Time (Months)';
    const value = isTime ? `${data.value} months` : formatCurrency(data.value);
    const name = isTime ? "Time" : "Interest";
      
    return (
      <div className="p-2 bg-white border border-neutral-300 rounded-md shadow-lg text-sm">
        <p className="label font-semibold text-neutral-700">{`${label}`}</p>
        <p className="intro text-neutral-600">{`${name} : ${value}`}</p>
      </div>
    );
  }
  return null;
};


function DebtOptimiser() {
  const { wallet, apiUrl } = useWallet();
  const walletId = wallet ? wallet.wallet_id : null;

  const [budget, setBudget] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loansLoading, setLoansLoading] = useState(false); // For fetching loans
  const [chartData, setChartData] = useState([]);
  const [noLoansFound, setNoLoansFound] = useState(false);
  const [totalMinimumPayment, setTotalMinimumPayment] = useState(0);
  const [loans, setLoans] = useState([]); // Keep loans state

  // --- Fetch loans when walletId changes ---
  useEffect(() => {
    if (walletId) {
      fetchApprovedLoans();
    } else {
      setLoans([]);
      setResults(null);
      setTotalMinimumPayment(0);
      setNoLoansFound(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]);

  // --- Calculate total minimum payment when loans change ---
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
  
  // --- Format data for charts ---
  useEffect(() => {
    if (results) {
      const data = [
        {
          name: 'Avalanche',
          'Payoff Time (Months)': results.avalanche_plan.months_to_payoff,
          'Total Interest Paid': parseFloat(results.avalanche_plan.total_interest_paid),
        },
        {
          name: 'Snowball',
          'Payoff Time (Months)': results.snowball_plan.months_to_payoff,
          'Total Interest Paid': parseFloat(results.snowball_plan.total_interest_paid),
        },
      ];
      setChartData(data);
    } else {
      setChartData([]);
    }
  }, [results]);

  // --- Function to fetch approved loans ---
  const fetchApprovedLoans = async () => {
    setLoansLoading(true);
    setResults(null);
    setNoLoansFound(false);
    try {
      const response = await fetch(`${apiUrl}/loan/by-wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      const approvedLoans = Array.isArray(data) ? data.filter(loan => loan.status === 'APPROVED') : [];
      setLoans(approvedLoans);
      if (approvedLoans.length === 0) {
        setNoLoansFound(true);
      }
    } catch (e) {
      toast.error(`Failed to fetch loans: ${e.message}`);
      setLoans([]);
    } finally {
      setLoansLoading(false);
    }
  };

  // --- Calculate Repayment Plan ---
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
    setNoLoansFound(false);

    const calculationToastId = toast.loading('Calculating plans...');

    try {
      const response = await fetch(`${apiUrl}/debt-optimiser`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_id: walletId,
          monthly_budget: totalBudget.toFixed(2),
        }),
      });
      
      const responseBody = await response.json();

      if (!response.ok) {
        if (response.status === 404) {
          setNoLoansFound(true);
          toast.dismiss(calculationToastId);
        } 
        else if (response.status === 400 && responseBody.total_minimum_payment) {
          const minPayment = formatCurrency(responseBody.total_minimum_payment);
          throw new Error(`Budget is too low. Total minimum payment is ${minPayment}.`);
        }
        else {
          throw new Error(responseBody.message || `HTTP error! Status: ${response.status}`);
        }
      } else {
        setResults(responseBody);
        toast.success(<b>Calculation complete!</b>, { id: calculationToastId });
      }
    } catch (error) {
      console.error("Calculation failed:", error);
      toast.error(<b>{error.message}</b>, { id: calculationToastId });
    } finally {
      setLoading(false);
    }
  };

  // --- UPDATED Recommendation Helper ---
  const getRecommendation = () => {
    if (!results) return null;

    const { avalanche_plan, snowball_plan, summary } = results;
    if (summary.extra_payment <= 0) {
        return (
             <div className="mt-6 text-center p-3 bg-blue-50 border border-blue-200 rounded-md">
                <p className="font-semibold text-blue-800">
                    You are paying the minimums. Add an extra payment to see how these plans differ!
                </p>
            </div>
        );
    }
    
    // Choose the winner
    const avalanche_is_better = parseFloat(avalanche_plan.total_interest_paid) < parseFloat(snowball_plan.total_interest_paid);
    const winner = avalanche_is_better ? avalanche_plan : snowball_plan;
    const winner_name = avalanche_is_better ? "Avalanche" : "Snowball";
    const target = winner.first_target;
    
    if (!target) {
        return <p className="text-accent-red-dark">Could not determine target loan.</p>;
    }
    
    const target_desc = winner_name === 'Avalanche'
      ? `(your highest interest loan at ${target.interest_rate}%)`
      : `(your lowest balance loan at ${formatCurrency(target.remaining_balance)})`;

    return (
      <div className="mt-6 text-left p-4 bg-accent-green-light border border-accent-green/50 rounded-md">
        <h4 className="font-semibold text-accent-green-dark mb-2">Your Recommended Plan: {winner_name}</h4>
        <p className="text-sm text-neutral-700">
          Pay the minimum on all loans, then pay your extra <b className="text-accent-green-dark">{formatCurrency(summary.extra_payment)}</b> towards:
        </p>
        <p className="text-sm font-semibold text-neutral-800 mt-1 pl-2">
          {target.name} {target_desc}
        </p>

        {/* --- NEW: Payoff Timeline --- */}
        {winner.payoff_log && winner.payoff_log.length > 0 && (
          <div className="mt-4 pt-3 border-t border-accent-green/50">
            <h5 className="font-semibold text-neutral-700 text-sm mb-2">Payoff Timeline:</h5>
            <ul className="list-disc list-inside space-y-1 text-sm text-neutral-600">
              {winner.payoff_log.map((logEntry, index) => (
                <li key={index}>{logEntry}</li>
              ))}
              <li key="final">Month {winner.months_to_payoff}: All loans paid off!</li>
            </ul>
          </div>
        )}
        {/* --- END: Payoff Timeline --- */}
        
      </div>
    );
  };
  // --- END HELPER ---

  // --- Render Logic ---
  if (!walletId) { return null; }

  // Show a loading spinner if still fetching the loans
  if (loansLoading) {
    return (
        <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
            <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Optimiser</h2>
            <Spinner />
        </div>
    );
  }

  // Show the "No Approved Loans" empty state
  if (noLoansFound) {
      return (
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
              <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Optimiser</h2>
              <div className="text-center text-neutral-500 my-4 py-8">
                  <BanknotesIcon className="h-12 w-12 mx-auto text-neutral-400" />
                  <h3 className="mt-2 text-sm font-semibold text-neutral-700">No Approved Loans Found</h3>
                  <p className="mt-1 text-sm text-neutral-500">You need approved loans to use the optimiser.</p>
                  <p className="mt-1 text-sm text-neutral-500">Visit the 'Loans' tab to apply for a loan.</p>
              </div>
          </div>
      );
  }

  // --- Main Component Render (if loans exist) ---
  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Optimiser</h2>

      {/* --- Input Form --- */}
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
            disabled={loading} // Check general loading
            className="px-4 py-2 bg-teal-500 text-white rounded-md hover:bg-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:bg-teal-300 flex-shrink-0"
          >
            {loading ? (
                <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Calculating...
                </span>
            ) : (
                'Calculate Plans'
            )}
          </button>
        </div>
      </form>
      
      {/* Show spinner IF loading AND results are not yet available */}
      {loading && !results && ( <Spinner /> )}

      {/* --- Display Results --- */}
      {results && !loading && (
        <div className="mt-6">
           <h3 className="text-lg font-semibold text-neutral-800 mb-4 text-center">Comparison Results</h3>
            {/* Summary Section */}
            <div className="mb-6 p-4 bg-white border border-neutral-200 rounded-md shadow-sm text-sm">
                <h4 className="font-medium text-neutral-700 mb-2">Summary</h4>
                <p className="text-neutral-600">Total Approved Loans: <span className="font-semibold text-neutral-800">{results.summary.total_loans}</span></p>
                <p className="text-neutral-600">Total Minimum Payment: <span className="font-semibold text-neutral-800">{formatCurrency(results.summary.total_minimum_payment)}</span></p>
                <p className="text-neutral-600">Your Total Monthly Payment: <span className="font-semibold text-neutral-800">{formatCurrency(results.summary.monthly_budget)}</span></p>
                <p className="text-neutral-600">Extra Payment Applied: <span className="font-semibold text-accent-green-dark">{formatCurrency(results.summary.extra_payment)}</span></p>
            </div>
            
             {/* --- Charts --- */}
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Chart 1: Payoff Time */}
                <div className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                    <h4 className="font-medium text-neutral-700 mb-4 text-center">Payoff Time (Months)</h4>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" />
                        <XAxis dataKey="name" stroke="#4b5563" />
                        <YAxis stroke="#4b5563" allowDecimals={false} tickFormatter={(value) => `${value} mo`} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="Payoff Time (Months)" fill="#3b82f6" name="Time" />
                      </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Chart 2: Total Interest */}
                <div className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                   <h4 className="font-medium text-neutral-700 mb-4 text-center">Total Interest Paid ($)</h4>
                   <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" />
                        <XAxis dataKey="name" stroke="#4b5563" />
                        <YAxis stroke="#4b5563" allowDecimals={false} tickFormatter={(value) => `$${value}`} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="Total Interest Paid" fill="#8b5cf6" name="Interest" />
                      </BarChart>
                    </ResponsiveContainer>
                </div>
             </div>
             {/* --- End Charts --- */}

             {/* --- Recommendation --- */}
             {getRecommendation()}
             {/* --- End Recommendation --- */}
        </div>
      )}
    </div>
  );
}

export default DebtOptimiser;