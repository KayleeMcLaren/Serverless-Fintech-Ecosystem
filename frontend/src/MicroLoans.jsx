import React, { useState, useEffect } from 'react';

// Keep formatCurrency helper
const formatCurrency = (amount) => {
  try {
    const numberAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numberAmount)) return String(amount);
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numberAmount);
  } catch (e) {
    return String(amount);
  }
};

function MicroLoans({ walletId, apiUrl }) {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newLoanAmount, setNewLoanAmount] = useState('');
  const [newLoanRate, setNewLoanRate] = useState('');
  const [newLoanMinPayment, setNewLoanMinPayment] = useState('');

  // --- Keep useEffect, fetchLoans, handleApplyLoan, handleLoanAction ---
  // --- No changes needed in the JavaScript logic itself ---
   useEffect(() => {
    if (walletId) {
      fetchLoans();
    } else {
      setLoans([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]);

  const fetchLoans = async () => {
    if (!walletId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/loan/by-wallet/${encodeURIComponent(walletId)}`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      data.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
      setLoans(data);
    } catch (e) {
      setError(`Failed to fetch loans: ${e.message}`);
      setLoans([]);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyLoan = async (e) => {
    e.preventDefault();
    if (!walletId || !newLoanAmount || !newLoanRate || !newLoanMinPayment ||
        parseFloat(newLoanAmount) <= 0 || parseFloat(newLoanRate) < 0 || parseFloat(newLoanMinPayment) <= 0) {
      setError('Please provide valid positive values for amount, rate, and minimum payment.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/loan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_id: walletId,
          amount: parseFloat(newLoanAmount).toFixed(2),
          interest_rate: parseFloat(newLoanRate).toFixed(2),
          minimum_payment: parseFloat(newLoanMinPayment).toFixed(2),
        }),
      });
      const responseBody = await response.json();
      if (!response.ok) {
        throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
      }
      setNewLoanAmount('');
      setNewLoanRate('');
      setNewLoanMinPayment('');
      fetchLoans();
    } catch (e) {
      setError(`Failed to apply for loan: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLoanAction = async (loanId, action) => {
    if (!window.confirm(`Are you sure you want to ${action} this loan?`)) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/loan/${encodeURIComponent(loanId)}/${action}`, {
        method: 'POST',
      });
      const responseBody = await response.json();
      if (!response.ok) {
         const apiErrorMsg = responseBody?.message || `HTTP error! Status: ${response.status}`;
         throw new Error(apiErrorMsg);
      }
      fetchLoans();
    } catch (e) {
      setError(`Failed to ${action} loan: ${e.message}`);
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
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Micro-Loans</h2>

      {/* --- Loading and Error Display --- */}
      {loading && <p className="text-center text-primary-blue my-4">Loading loans...</p>}
      {/* Use accent-red colors for error */}
      {error && (
        <p className="my-4 p-3 bg-accent-red-light border border-accent-red text-accent-red-dark rounded-md text-sm text-left">
          {error}
        </p>
      )}

      {/* --- Display Existing Loans --- */}
      {!loading && loans.length === 0 && (
        <p className="text-center text-neutral-500 my-4">No loans found for this wallet.</p>
      )}
      {!loading && loans.length > 0 && (
        <div className="space-y-4 mb-6">
          {loans.map((loan) => (
             // Use neutral colors for loan item
            <div key={loan.loan_id} className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
              <div className="flex justify-between items-start mb-2">
                 {/* Status Badge - Use theme colors */}
                <span className={`text-xs font-medium px-2.5 py-0.5 rounded ${ // Adjusted padding/size
                  loan.status === 'APPROVED' ? 'bg-accent-green-light text-accent-green-dark' :
                  loan.status === 'REJECTED' ? 'bg-accent-red-light text-accent-red-dark' :
                  'bg-yellow-100 text-yellow-800' // Keep yellow for PENDING
                }`}>
                  {loan.status}
                </span>
                {loan.status === 'PENDING' && !loading && (
                   <div className="flex gap-2">
                     <button
                       onClick={() => handleLoanAction(loan.loan_id, 'approve')}
                       // Use accent-green button styles
                       className="px-2 py-1 bg-accent-green text-white text-xs rounded hover:bg-accent-green-dark disabled:bg-accent-green-light disabled:cursor-not-allowed disabled:text-neutral-500"
                       disabled={loading}
                      >
                       Approve
                     </button>
                     <button
                       onClick={() => handleLoanAction(loan.loan_id, 'reject')}
                       // Use accent-red button styles
                       className="px-2 py-1 bg-accent-red text-white text-xs rounded hover:bg-accent-red-dark disabled:bg-accent-red-light disabled:cursor-not-allowed disabled:text-neutral-500"
                       disabled={loading}
                      >
                       Reject
                     </button>
                   </div>
                 )}
              </div>
               {/* Use neutral text colors */}
              <p className="text-sm text-neutral-700">
                Amount: <span className="font-semibold">{formatCurrency(loan.amount)}</span>
                {loan.status === 'APPROVED' && ` (Balance: ${formatCurrency(loan.remaining_balance || loan.amount)})`}
              </p>
              <p className="text-xs text-neutral-500">
                Rate: {loan.interest_rate}% | Min. Payment: {formatCurrency(loan.minimum_payment)}
              </p>
               <p className="text-xs text-neutral-400 mt-1 truncate">ID: {loan.loan_id}</p>
            </div>
          ))}
        </div>
      )}

      {/* --- Form to Apply for New Loan --- */}
      <form onSubmit={handleApplyLoan} className="mt-6 pt-4 border-t border-neutral-200">
        <h4 className="text-md font-semibold text-neutral-700 mb-3">Apply for New Loan</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input
            type="number"
            value={newLoanAmount}
            onChange={(e) => setNewLoanAmount(e.target.value)}
            placeholder="Loan Amount ($)"
            disabled={loading}
            min="1" step="0.01" required
            // Use neutral border, primary focus
            className="p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
          />
          <input
            type="number"
            value={newLoanRate}
            onChange={(e) => setNewLoanRate(e.target.value)}
            placeholder="Interest Rate (%)"
            disabled={loading}
            min="0" step="0.01" required
             // Use neutral border, primary focus
            className="p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
          />
          <input
            type="number"
            value={newLoanMinPayment}
            onChange={(e) => setNewLoanMinPayment(e.target.value)}
            placeholder="Min. Payment ($)"
            disabled={loading}
            min="1" step="0.01" required
             // Use neutral border, primary focus
            className="p-2 border border-neutral-300 rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
          />
        </div>
        <div className="text-center">
          <button
            type="submit"
            disabled={loading || !newLoanAmount || !newLoanRate || !newLoanMinPayment}
            // Use primary blue button colors
            className="px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light disabled:cursor-not-allowed"
          >
            {loading ? 'Submitting...' : 'Apply for Loan'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default MicroLoans;