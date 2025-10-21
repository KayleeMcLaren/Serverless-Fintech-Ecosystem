import React, { useState, useEffect } from 'react';

// Helper to format currency
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
};

function MicroLoans({ walletId, apiUrl }) {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newLoanAmount, setNewLoanAmount] = useState('');
  const [newLoanRate, setNewLoanRate] = useState('');
  const [newLoanMinPayment, setNewLoanMinPayment] = useState('');

  // --- Fetch loans when walletId changes ---
  useEffect(() => {
    if (walletId) {
      fetchLoans();
    } else {
      setLoans([]); // Clear if no wallet ID
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId]);

  // --- Fetch Loans Function ---
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
      // Sort loans, maybe by created date or status
      data.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
      setLoans(data);
    } catch (e) {
      setError(`Failed to fetch loans: ${e.message}`);
      setLoans([]);
    } finally {
      setLoading(false);
    }
  };

  // --- Apply for Loan Function ---
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
      fetchLoans(); // Refetch to show the new pending loan
    } catch (e) {
      setError(`Failed to apply for loan: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // --- Approve/Reject Loan Function ---
  const handleLoanAction = async (loanId, action) => { // action is 'approve' or 'reject'
    if (!window.confirm(`Are you sure you want to ${action} this loan?`)) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/loan/${encodeURIComponent(loanId)}/${action}`, {
        method: 'POST', // Both approve and reject use POST
      });
      const responseBody = await response.json(); // Read body even for errors
      if (!response.ok) {
         // Handle 409 Conflict specifically
        const apiErrorMsg = responseBody?.message || `HTTP error! Status: ${response.status}`;
         throw new Error(apiErrorMsg);
      }
      fetchLoans(); // Refetch loans to update status
    } catch (e) {
      setError(`Failed to ${action} loan: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };


  // --- Render Logic ---
  if (!walletId) {
    // Don't render anything or show a placeholder if no wallet is active
    return null;
    // Or return a message:
    // return <div className="..."><p>Load a wallet to view loans.</p></div>;
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8 shadow-sm">
      <h2 className="text-xl font-semibold text-gray-700 mb-6 text-center">Micro-Loans</h2>

      {/* --- Loading and Error Display --- */}
      {loading && <p className="text-center text-blue-600 my-4">Loading loans...</p>}
      {error && (
        <p className="my-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm text-left">
          {error}
        </p>
      )}

      {/* --- Display Existing Loans --- */}
      {!loading && loans.length === 0 && (
        <p className="text-center text-gray-500 my-4">No loans found for this wallet.</p>
      )}
      {!loading && loans.length > 0 && (
        <div className="space-y-4 mb-6">
          {loans.map((loan) => (
            <div key={loan.loan_id} className="p-4 bg-white border border-gray-200 rounded-md shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className={`text-sm font-medium px-2 py-0.5 rounded ${
                  loan.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                  loan.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800' // PENDING
                }`}>
                  {loan.status}
                </span>
                {loan.status === 'PENDING' && !loading && (
                   <div className="flex gap-2">
                     <button
                       onClick={() => handleLoanAction(loan.loan_id, 'approve')}
                       className="px-2 py-1 bg-green-500 text-white text-xs rounded hover:bg-green-600 disabled:bg-green-300"
                       disabled={loading}
                      >
                       Approve
                     </button>
                     <button
                       onClick={() => handleLoanAction(loan.loan_id, 'reject')}
                       className="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 disabled:bg-red-300"
                       disabled={loading}
                      >
                       Reject
                     </button>
                   </div>
                 )}
              </div>
              <p className="text-sm text-gray-700">
                Amount: <span className="font-semibold">{formatCurrency(loan.amount)}</span>
                {loan.status === 'APPROVED' && ` (Balance: ${formatCurrency(loan.remaining_balance || loan.amount)})`}
              </p>
              <p className="text-xs text-gray-500">
                Rate: {loan.interest_rate}% | Min. Payment: {formatCurrency(loan.minimum_payment)}
              </p>
               <p className="text-xs text-gray-400 mt-1">ID: {loan.loan_id}</p>
            </div>
          ))}
        </div>
      )}

      {/* --- Form to Apply for New Loan --- */}
      <form onSubmit={handleApplyLoan} className="mt-6 pt-4 border-t border-gray-200">
        <h4 className="text-md font-semibold text-gray-700 mb-3">Apply for New Loan</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input
            type="number"
            value={newLoanAmount}
            onChange={(e) => setNewLoanAmount(e.target.value)}
            placeholder="Loan Amount ($)"
            disabled={loading}
            min="1" step="0.01" required
            className="p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
          />
          <input
            type="number"
            value={newLoanRate}
            onChange={(e) => setNewLoanRate(e.target.value)}
            placeholder="Interest Rate (%)"
            disabled={loading}
            min="0" step="0.01" required
            className="p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
          />
          <input
            type="number"
            value={newLoanMinPayment}
            onChange={(e) => setNewLoanMinPayment(e.target.value)}
            placeholder="Min. Payment ($)"
            disabled={loading}
            min="1" step="0.01" required
            className="p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
          />
        </div>
        <div className="text-center">
          <button
            type="submit"
            disabled={loading || !newLoanAmount || !newLoanRate || !newLoanMinPayment}
            className="px-4 py-2 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:bg-indigo-300"
          >
            {loading ? 'Submitting...' : 'Apply for Loan'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default MicroLoans;