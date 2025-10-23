import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import Spinner from './Spinner';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
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
  const { wallet, apiUrl } = useWallet(); // Get wallet and apiUrl
  const walletId = wallet ? wallet.wallet_id : null; // Get walletId from wallet

  const [budget, setBudget] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState([]);
  const [noLoansFound, setNoLoansFound] = useState(false); // State for empty

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

  // --- Calculate Repayment Plan ---
  const handleCalculate = async (e) => {
    e.preventDefault();
    if (!walletId || !budget || parseFloat(budget) <= 0) {
      toast.error('Please provide a valid wallet ID and a positive monthly budget.');
      setResults(null);
      return;
    }
    setLoading(true);
    setResults(null); // Clear previous results
    setNoLoansFound(false); // Reset empty state

    const calculationToastId = toast.loading('Calculating plans...');

    try {
      const response = await fetch(`${apiUrl}/debt-optimiser`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_id: walletId,
          monthly_budget: parseFloat(budget).toFixed(2),
        }),
      });
      
      const responseBody = await response.json();

      if (!response.ok) {
        // Check for 404 (No Loans Found)
        if (response.status === 404) {
          setNoLoansFound(true); // Set the empty state
          toast.dismiss(calculationToastId); // Dismiss loading toast
        } 
        // Handle 400 (Budget too low)
        else if (response.status === 400 && responseBody.total_minimum_payment) {
          const minPayment = formatCurrency(responseBody.total_minimum_payment);
          throw new Error(`Budget is too low. Total minimum payment is ${minPayment}.`);
        }
        // Handle other errors
        else {
          throw new Error(responseBody.message || `HTTP error! Status: ${response.status}`);
        }
      } else {
        // Success
        setResults(responseBody);
        toast.success(<b>Calculation complete!</b>, { id: calculationToastId });
      }
    } catch (error) {
      console.error("Calculation failed:", error);
      toast.error(<b>{error.message}</b>, { id: calculationToastId });
    } finally {
      setLoading(false); // Stop loading state
    }
  };

  // --- Render Logic ---
  if (!walletId) { return null; }

  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Optimiser</h2>

      {/* --- Input Form --- */}
      <form onSubmit={handleCalculate} className="mb-6 pb-4 border-b border-neutral-200">
        <h4 className="text-md font-semibold text-neutral-700 mb-3">Calculate Payoff Plan</h4>
        <div className="flex flex-wrap gap-3 mb-3 items-stretch">
          <input
            type="number" value={budget} onChange={(e) => setBudget(e.target.value)}
            placeholder="Total Monthly Budget ($)" disabled={loading}
            min="1" step="0.01" required
            className="flex-grow basis-40 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
          />
          <button
            type="submit" disabled={loading || !budget}
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

      {/* --- Empty State for No Loans --- */}
      {noLoansFound && !loading && (
        <div className="text-center text-neutral-500 my-4 py-8">
            <BanknotesIcon className="h-12 w-12 mx-auto text-neutral-400" />
            <h3 className="mt-2 text-sm font-semibold text-neutral-700">No Approved Loans Found</h3>
            <p className="mt-1 text-sm text-neutral-500">You need approved loans to use the optimiser.</p>
            <p className="mt-1 text-sm text-neutral-500">Visit the 'Loans' tab to apply for a loan.</p>
        </div>
      )}

      {/* Show spinner IF loading AND results are not yet available */}
      {loading && !results && !noLoansFound && (
        <Spinner />
      )}

      {/* --- Display Results --- */}
      {results && !loading && (
        <div className="mt-6">
           <h3 className="text-lg font-semibold text-neutral-800 mb-4 text-center">Comparison Results</h3>
            <div className="mb-6 p-4 bg-white border border-neutral-200 rounded-md shadow-sm text-sm">
                <h4 className="font-medium text-neutral-700 mb-2">Summary</h4>
                <p className="text-neutral-600">Total Approved Loans: <span className="font-semibold text-neutral-800">{results.summary.total_loans}</span></p>
                <p className="text-neutral-600">Total Minimum Payment: <span className="font-semibold text-neutral-800">{formatCurrency(results.summary.total_minimum_payment)}</span></p>
                <p className="text-neutral-600">Your Monthly Budget: <span className="font-semibold text-neutral-800">{formatCurrency(results.summary.monthly_budget)}</span></p>
                <p className="text-neutral-600">Extra Payment Applied: <span className="font-semibold text-accent-green-dark">{formatCurrency(results.summary.extra_payment)}</span></p>
            </div>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-4 bg-primary-blue-light/20 border border-primary-blue/30 rounded-md shadow-sm">
                  <h4 className="font-medium text-primary-blue-dark mb-2">Avalanche Plan</h4>
                  <p className="text-sm text-neutral-700">Payoff Time: <span className="font-semibold text-neutral-900">{results.avalanche_plan.months_to_payoff} months</span></p>
                  <p className="text-sm text-neutral-700">Total Interest Paid: <span className="font-semibold text-neutral-900">{formatCurrency(results.avalanche_plan.total_interest_paid)}</span></p>
                  <p className="text-xs text-neutral-500 mt-1">(Targets highest interest rate first)</p>
                </div>
                <div className="p-4 bg-purple-50 border border-purple-200 rounded-md shadow-sm">
                  <h4 className="font-medium text-purple-800 mb-2">Snowball Plan</h4>
                  <p className="text-sm text-neutral-700">Payoff Time: <span className="font-semibold text-neutral-900">{results.snowball_plan.months_to_payoff} months</span></p>
                  <p className="text-sm text-neutral-700">Total Interest Paid: <span className="font-semibold text-neutral-900">{formatCurrency(results.snowball_plan.total_interest_paid)}</span></p>
                   <p className="text-xs text-neutral-500 mt-1">(Targets lowest balance first)</p>
                </div>
             </div>
              <div className="mt-6 text-center p-3 bg-accent-green-light border border-accent-green/50 rounded-md">
                <p className="font-semibold text-accent-green-dark">
                    Recommendation: The '{parseFloat(results.avalanche_plan.total_interest_paid) < parseFloat(results.snowball_plan.total_interest_paid) ? 'Avalanche' : 'Snowball'}'
                    plan will likely save you the most money on interest.
                </p>
            </div>
        </div>
      )}
    </div>
  );
}

export default DebtOptimiser;