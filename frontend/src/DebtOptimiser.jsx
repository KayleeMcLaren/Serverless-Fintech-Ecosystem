import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import Spinner from './Spinner'; // Make sure Spinner is imported
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

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

// --- Custom Tooltip for Charts ---
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0]; // Get data for the bar
    // data.dataKey will be "Payoff Time (Months)" or "Total Interest Paid"
    const isTime = data.dataKey === 'Payoff Time (Months)';
    const value = isTime ? `${data.value} months` : formatCurrency(data.value);
    const name = isTime ? "Time" : "Interest";
      
    return (
      <div className="p-2 bg-white border border-neutral-300 rounded-md shadow-lg text-sm">
        <p className="label font-semibold text-neutral-700">{`${label}`}</p>
        <p className="intro text-neutral-600">{`${data.name} : ${value}`}</p>
      </div>
    );
  }
  return null;
};

function DebtOptimiser({ walletId, apiUrl }) {
  const [budget, setBudget] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState([]);

  // --- Format data for charts when results change ---
  useEffect(() => {
    if (results) {
      // Format data for charts
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
      setChartData([]); // Clear chart data if no results
    }
  }, [results]); // Dependency: results

  // --- Calculate Repayment Plan (Use Toast) ---
  const handleCalculate = async (e) => {
    e.preventDefault();
    if (!walletId || !budget || parseFloat(budget) <= 0) {
      toast.error('Please provide a valid wallet ID and a positive monthly budget.');
      setResults(null);
      return;
    }
    setLoading(true); // <-- 1. Loading starts
    setResults(null); // Clear previous results

    // --- ADD try...finally block ---
    try {
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
                const error = new Error(responseBody.message || `HTTP error! Status: ${response.status}`);
                error.responseBody = responseBody;
                throw error;
              }
              return responseBody; // Pass results data
          })
          .then((data) => {
              setResults(data); // Set results on success
          }),
          {
              loading: 'Calculating plans...',
              success: <b>Calculation complete!</b>,
              error: (err) => {
                // Check if our custom data exists
                if (err.responseBody && err.responseBody.total_minimum_payment) {
                    const minPayment = formatCurrency(err.responseBody.total_minimum_payment);
                    // Return the more descriptive error message
                    return <b>Budget is too low. Total minimum payment is {minPayment}.</b>;
                }
                // Fallback for other errors
                return <b>{err.message || 'Calculation failed'}</b>;
              },
          }
      );
    } catch (error) {
        // We just need to catch the error that toast.promise re-throws
        // to allow the 'finally' block to run.
        // We don't need to show another toast here.
        console.error("Calculation failed (caught in try/catch):", error);
    } finally {
        setLoading(false); // <-- 3. This will now run even if the promise fails
    }
    // --- END FIX ---
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
             {/* --- NEW: Charts Section --- */}
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Chart 1: Payoff Time */}
                <div className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                    <h4 className="font-medium text-neutral-700 mb-4 text-center">Payoff Time (Months)</h4>
                    {/* --- FIX 2: Adjusted margin and YAxis --- */}
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}> {/* Slightly adjusted left margin */}
                        <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" />
                        <XAxis dataKey="name" stroke="#4b5563" />
                        <YAxis stroke="#4b5563" allowDecimals={false} tickFormatter={(value) => `${value} mo`} /> {/* Use tickFormatter */}
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="Payoff Time (Months)" fill="#3b82f6" name="Time" />
                      </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Chart 2: Total Interest */}
                <div className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                   <h4 className="font-medium text-neutral-700 mb-4 text-center">Total Interest Paid ($)</h4>
                   {/* --- FIX 2: Adjusted margin and YAxis --- */}
                   <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}> {/* Increased left margin */}
                        <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" />
                        <XAxis dataKey="name" stroke="#4b5563" />
                        <YAxis stroke="#4b5563" allowDecimals={false} tickFormatter={(value) => `$${value}`} /> {/* Use tickFormatter */}
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="Total Interest Paid" fill="#8b5cf6" name="Interest" />
                      </BarChart>
                    </ResponsiveContainer>
                </div>
             </div>
             {/* --- End Charts Section --- */}

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