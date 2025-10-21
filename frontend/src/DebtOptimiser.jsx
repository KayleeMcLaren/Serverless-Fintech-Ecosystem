import React, { useState } from 'react';

// Helper to format currency
const formatCurrency = (amount) => {
  try {
    // Attempt to convert to number if it's a string representation
    const numberAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numberAmount)) return String(amount); // Handle non-numeric gracefully
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numberAmount);
  } catch (e) {
    console.error("Error formatting currency:", amount, e);
    return String(amount); // Fallback
  }
};

function DebtOptimiser({ walletId, apiUrl }) {
  const [budget, setBudget] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- Calculate Repayment Plan Function ---
  const handleCalculate = async (e) => {
    e.preventDefault();
    if (!walletId || !budget || parseFloat(budget) <= 0) {
      setError('Please provide a valid wallet ID and a positive monthly budget.');
      setResults(null);
      return;
    }
    setLoading(true);
    setError(null);
    setResults(null); // Clear previous results
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
    return null; // Don't render if no wallet is active
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-gray-700 mb-6 text-center">Debt Repayment Optimiser</h2>

      {/* --- Input Form --- */}
      <form onSubmit={handleCalculate} className="mb-6 pb-4 border-b border-gray-200">
        <h4 className="text-md font-semibold text-gray-700 mb-3">Calculate Payoff Plan</h4>
        <div className="flex flex-wrap gap-3 mb-3 items-stretch">
          <input
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="Total Monthly Budget ($)"
            disabled={loading}
            min="1" step="0.01" required
            className="flex-grow basis-40 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 min-w-[150px]"
          />
          <button
            type="submit"
            disabled={loading || !budget}
            className="px-4 py-2 bg-teal-500 text-white rounded-md hover:bg-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:bg-teal-300 flex-shrink-0"
          >
            {loading ? 'Calculating...' : 'Calculate Plans'}
          </button>
        </div>
      </form>

      {/* --- Loading and Error Display --- */}
      {loading && <p className="text-center text-blue-600 my-4">Calculating repayment plans...</p>}
      {error && (
        <p className="my-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm text-left">
          {error}
        </p>
      )}

      {/* --- Display Results --- */}
      {results && !loading && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 text-center">Comparison Results</h3>

          {/* Summary Section */}
          <div className="mb-6 p-4 bg-white border border-gray-200 rounded-md shadow-sm text-sm">
              <h4 className="font-medium text-gray-700 mb-2">Summary</h4>
              <p>Total Approved Loans: <span className="font-semibold">{results.summary.total_loans}</span></p>
              <p>Total Minimum Payment: <span className="font-semibold">{formatCurrency(results.summary.total_minimum_payment)}</span></p>
              <p>Your Monthly Budget: <span className="font-semibold">{formatCurrency(results.summary.monthly_budget)}</span></p>
              <p>Extra Payment Applied: <span className="font-semibold text-green-600">{formatCurrency(results.summary.extra_payment)}</span></p>
          </div>

          {/* Results Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Avalanche Plan */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-md shadow-sm">
              <h4 className="font-medium text-blue-800 mb-2">Avalanche Plan</h4>
              <p className="text-sm">Payoff Time: <span className="font-semibold">{results.avalanche_plan.months_to_payoff} months</span></p>
              <p className="text-sm">Total Interest Paid: <span className="font-semibold">{formatCurrency(results.avalanche_plan.total_interest_paid)}</span></p>
              <p className="text-xs text-gray-500 mt-1">(Targets highest interest rate first)</p>
            </div>

            {/* Snowball Plan */}
            <div className="p-4 bg-purple-50 border border-purple-200 rounded-md shadow-sm">
              <h4 className="font-medium text-purple-800 mb-2">Snowball Plan</h4>
              <p className="text-sm">Payoff Time: <span className="font-semibold">{results.snowball_plan.months_to_payoff} months</span></p>
              <p className="text-sm">Total Interest Paid: <span className="font-semibold">{formatCurrency(results.snowball_plan.total_interest_paid)}</span></p>
               <p className="text-xs text-gray-500 mt-1">(Targets lowest balance first)</p>
            </div>
          </div>

           {/* Recommendation (Simple Example) */}
           <div className="mt-6 text-center p-3 bg-green-50 border border-green-200 rounded-md">
                <p className="font-semibold text-green-800">
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