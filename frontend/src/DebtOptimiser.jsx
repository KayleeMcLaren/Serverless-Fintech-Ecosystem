import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import Spinner from './Spinner'; // Make sure Spinner is imported

// Keep formatCurrency helper
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

function DebtOptimiser({ walletId, apiUrl }) {
  const [budget, setBudget] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  // const [error, setError] = useState(null); // Replaced by toasts

  // --- Calculate Repayment Plan (Use Toast) ---
  const handleCalculate = async (e) => {
    e.preventDefault();
    if (!walletId || !budget || parseFloat(budget) <= 0) {
      toast.error('Please provide a valid wallet ID and a positive monthly budget.');
      setResults(null);
      return;
    }
    setLoading(true);
    setResults(null); // Clear previous results

    await toast.promise(
        fetch(`${apiUrl}/debt-optimiser`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              wallet_id: walletId,
              monthly_budget: parseFloat(budget).toFixed(2),
            }),
        })
        .then(async (response) => {
            const responseBody = await response.json();
            if (!response.ok) {
                throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
            }
            return responseBody; // Pass results data
        })
        .then((data) => {
            setResults(data); // Set results on success
        }),
        {
            loading: 'Calculating plans...',
            success: <b>Calculation complete!</b>,
            error: (err) => <b>Calculation failed: {err.message}</b>,
        }
    );
    setLoading(false);
  };


  // --- Render Logic ---
  if (!walletId) { return null; }

  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Optimiser</h2>

      {/* --- Input Form --- */}
      <form onSubmit={handleCalculate} className="mb-6 pb-4 border-b border-neutral-200">
         {/* ... (Keep form JSX the same) ... */}
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
            {/* Show spinner *inside* button when loading */}
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

      {/* --- Display Loading Spinner OR Results --- */}
      
      {/* Show spinner IF loading AND results are not yet available */}
      {loading && !results && (
        <Spinner />
      )}

      {/* Show results IF NOT loading AND results ARE available */}
      {results && !loading && (
        <div className="mt-6">
           {/* ... (Keep results display JSX the same) ... */}
           <h3 className="text-lg font-semibold text-neutral-800 mb-4 text-center">Comparison Results</h3>
            <div className="mb-6 p-4 bg-white border border-neutral-200 rounded-md shadow-sm text-sm">
                {/* ... Summary ... */}
                <h4 className="font-medium text-neutral-700 mb-2">Summary</h4>
                <p className="text-neutral-600">Total Approved Loans: <span className="font-semibold text-neutral-800">{results.summary.total_loans}</span></p>
                <p className="text-neutral-600">Total Minimum Payment: <span className="font-semibold text-neutral-800">{formatCurrency(results.summary.total_minimum_payment)}</span></p>
                <p className="text-neutral-600">Your Monthly Budget: <span className="font-semibold text-neutral-800">{formatCurrency(results.summary.monthly_budget)}</span></p>
                <p className="text-neutral-600">Extra Payment Applied: <span className="font-semibold text-accent-green-dark">{formatCurrency(results.summary.extra_payment)}</span></p>
            </div>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* ... Avalanche Plan ... */}
                <div className="p-4 bg-primary-blue-light/20 border border-primary-blue/30 rounded-md shadow-sm">
                  <h4 className="font-medium text-primary-blue-dark mb-2">Avalanche Plan</h4>
                  <p className="text-sm text-neutral-700">Payoff Time: <span className="font-semibold text-neutral-900">{results.avalanche_plan.months_to_payoff} months</span></p>
                  <p className="text-sm text-neutral-700">Total Interest Paid: <span className="font-semibold text-neutral-900">{formatCurrency(results.avalanche_plan.total_interest_paid)}</span></p>
                  <p className="text-xs text-neutral-500 mt-1">(Targets highest interest rate first)</p>
                </div>
                {/* ... Snowball Plan ... */}
                <div className="p-4 bg-purple-50 border border-purple-200 rounded-md shadow-sm">
                  <h4 className="font-medium text-purple-800 mb-2">Snowball Plan</h4>
                  <p className="text-sm text-neutral-700">Payoff Time: <span className="font-semibold text-neutral-900">{results.snowball_plan.months_to_payoff} months</span></p>
                  <p className="text-sm text-neutral-700">Total Interest Paid: <span className="font-semibold text-neutral-900">{formatCurrency(results.snowball_plan.total_interest_paid)}</span></p>
                   <p className="text-xs text-neutral-500 mt-1">(Targets lowest balance first)</p>
                </div>
             </div>
              {/* ... Recommendation ... */}
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