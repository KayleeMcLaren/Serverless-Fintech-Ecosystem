import React, { useState } from 'react';

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
  const [error, setError] = useState(null);

  // --- Keep handleCalculate ---
  // --- No changes needed in the JavaScript logic itself ---
   const handleCalculate = async (e) => {
    e.preventDefault();
    if (!walletId || !budget || parseFloat(budget) <= 0) {
      setError('Please provide a valid wallet ID and a positive monthly budget.');
      setResults(null);
      return;
    }
    setLoading(true);
    setError(null);
    setResults(null);
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
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      setResults(responseBody);
    } catch (e) {
      setError(`Failed to calculate plans: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };


  // --- Render Logic ---
  if (!walletId) {
    return null;
  }

  return (
    // Use neutral colors for card
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Debt Repayment Optimiser</h2>

      {/* --- Input Form --- */}
      <form onSubmit={handleCalculate} className="mb-6 pb-4 border-b border-neutral-200">
        <h4 className="text-md font-semibold text-neutral-700 mb-3">Calculate Payoff Plan</h4>
        <div className="flex flex-wrap gap-3 mb-3 items-stretch">
          <input
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="Total Monthly Budget ($)"
            disabled={loading}
            min="1" step="0.01" required
            // Use neutral border, primary focus
            className="flex-grow basis-40 p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
          />
          <button
            type="submit"
            disabled={loading || !budget}
            // Use different color, e.g., teal or primary blue
            className="px-4 py-2 bg-teal-500 text-white rounded-md hover:bg-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:bg-teal-300 flex-shrink-0"
          >
            {loading ? 'Calculating...' : 'Calculate Plans'}
          </button>
        </div>
      </form>

      {/* --- Loading and Error Display --- */}
      {loading && <p className="text-center text-primary-blue my-4">Calculating repayment plans...</p>}
      {/* Use accent-red for error */}
      {error && (
        <p className="my-4 p-3 bg-accent-red-light border border-accent-red text-accent-red-dark rounded-md text-sm text-left">
          {error}
        </p>
      )}

      {/* --- Display Results --- */}
      {results && !loading && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-neutral-800 mb-4 text-center">Comparison Results</h3>

          {/* Summary Section - Use neutral colors */}
          <div className="mb-6 p-4 bg-white border border-neutral-200 rounded-md shadow-sm text-sm">
              <h4 className="font-medium text-neutral-700 mb-2">Summary</h4>
              <p className="text-neutral-600">Total Approved Loans: <span className="font-semibold text-neutral-800">{results.summary.total_loans}</span></p>
              <p className="text-neutral-600">Total Minimum Payment: <span className="font-semibold text-neutral-800">{formatCurrency(results.summary.total_minimum_payment)}</span></p>
              <p className="text-neutral-600">Your Monthly Budget: <span className="font-semibold text-neutral-800">{formatCurrency(results.summary.monthly_budget)}</span></p>
              <p className="text-neutral-600">Extra Payment Applied: <span className="font-semibold text-accent-green-dark">{formatCurrency(results.summary.extra_payment)}</span></p>
          </div>

          {/* Results Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Avalanche Plan - Use primary blue theme */}
            <div className="p-4 bg-primary-blue-light/20 border border-primary-blue/30 rounded-md shadow-sm">
              <h4 className="font-medium text-primary-blue-dark mb-2">Avalanche Plan</h4>
              <p className="text-sm text-neutral-700">Payoff Time: <span className="font-semibold text-neutral-900">{results.avalanche_plan.months_to_payoff} months</span></p>
              <p className="text-sm text-neutral-700">Total Interest Paid: <span className="font-semibold text-neutral-900">{formatCurrency(results.avalanche_plan.total_interest_paid)}</span></p>
              <p className="text-xs text-neutral-500 mt-1">(Targets highest interest rate first)</p>
            </div>

            {/* Snowball Plan - Use different theme, e.g., purple or neutral */}
            <div className="p-4 bg-purple-50 border border-purple-200 rounded-md shadow-sm"> {/* Example: Purple theme */}
              <h4 className="font-medium text-purple-800 mb-2">Snowball Plan</h4>
              <p className="text-sm text-neutral-700">Payoff Time: <span className="font-semibold text-neutral-900">{results.snowball_plan.months_to_payoff} months</span></p>
              <p className="text-sm text-neutral-700">Total Interest Paid: <span className="font-semibold text-neutral-900">{formatCurrency(results.snowball_plan.total_interest_paid)}</span></p>
               <p className="text-xs text-neutral-500 mt-1">(Targets lowest balance first)</p>
            </div>
          </div>

           {/* Recommendation - Use accent green theme */}
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