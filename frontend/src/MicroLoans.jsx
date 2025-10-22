import React, { useState, useEffect } from 'react';

// --- Helper to format currency ---
const formatCurrency = (amount) => {
    try {
        // Ensure amount is treated as a number
        const numberAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
        if (isNaN(numberAmount)) {
            // Handle cases like 'N/A' or invalid strings gracefully
            return String(amount);
        }
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numberAmount);
    } catch (e) {
        console.error("Error formatting currency:", amount, e);
        return String(amount); // Fallback
    }
};

// --- Replicate Backend Rate Logic on Frontend ---
// Ensure this logic matches your backend calculate_interest_rate function
const calculateDisplayRate = (amount) => {
    const numAmount = parseFloat(amount || '0');
    if (numAmount < 500) return '25.0';
    if (numAmount < 2000) return '18.5';
    if (numAmount < 5000) return '15.0';
    return '12.5';
};
// ---

// --- Define Loan Amount Range ---
const MIN_LOAN_AMOUNT = 50;
const MAX_LOAN_AMOUNT = 10000;
const DEFAULT_LOAN_AMOUNT = 1000; // Starting point for slider
// ---

function MicroLoans({ walletId, apiUrl }) {
    const [loans, setLoans] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    // Initialize amount state with default
    const [newLoanAmount, setNewLoanAmount] = useState(String(DEFAULT_LOAN_AMOUNT));
    // State to display the calculated rate
    const [displayRate, setDisplayRate] = useState(calculateDisplayRate(DEFAULT_LOAN_AMOUNT));

    // --- Fetch loans when walletId changes ---
    useEffect(() => {
        if (walletId) {
            fetchLoans();
        } else {
            setLoans([]); // Clear if no wallet ID
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [walletId]);

    // --- Recalculate display rate when amount changes ---
    useEffect(() => {
        setDisplayRate(calculateDisplayRate(newLoanAmount));
    }, [newLoanAmount]); // Dependency: newLoanAmount

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
        // Validate only amount (rate/min payment are calculated backend)
        const amountNum = parseFloat(newLoanAmount);
        if (!walletId || !newLoanAmount || amountNum <= 0 || amountNum < MIN_LOAN_AMOUNT || amountNum > MAX_LOAN_AMOUNT ) {
          setError(`Please select a valid loan amount between ${formatCurrency(MIN_LOAN_AMOUNT)} and ${formatCurrency(MAX_LOAN_AMOUNT)}.`);
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
                    amount: amountNum.toFixed(2), // Send selected amount
                    // No need to send rate or min payment anymore
                }),
            });
            const responseBody = await response.json();
            if (!response.ok) {
                throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
            }
            // Reset amount slider to default
            setNewLoanAmount(String(DEFAULT_LOAN_AMOUNT));
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
        setLoading(true); // Consider a specific loading state per loan if needed
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
        <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
            <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Micro-Loans</h2>

            {/* --- Loading and Error Display --- */}
            {loading && <p className="text-center text-primary-blue my-4">Loading...</p>}
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
                        <div key={loan.loan_id} className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                            <div className="flex justify-between items-start mb-2">
                                {/* Status Badge */}
                                <span className={`text-xs font-medium px-2.5 py-0.5 rounded ${
                                    loan.status === 'APPROVED' ? 'bg-accent-green-light text-accent-green-dark' :
                                    loan.status === 'REJECTED' ? 'bg-accent-red-light text-accent-red-dark' :
                                    'bg-yellow-100 text-yellow-800' // PENDING
                                }`}>
                                    {loan.status}
                                </span>
                                {/* Approve/Reject Buttons for PENDING loans */}
                                {loan.status === 'PENDING' && !loading && (
                                     <div className="flex gap-2">
                                         <button
                                             onClick={() => handleLoanAction(loan.loan_id, 'approve')}
                                             className="px-2 py-1 bg-accent-green text-white text-xs rounded hover:bg-accent-green-dark disabled:bg-accent-green-light disabled:cursor-not-allowed disabled:text-neutral-500"
                                             disabled={loading}
                                            >
                                             Approve
                                         </button>
                                         <button
                                             onClick={() => handleLoanAction(loan.loan_id, 'reject')}
                                             className="px-2 py-1 bg-accent-red text-white text-xs rounded hover:bg-accent-red-dark disabled:bg-accent-red-light disabled:cursor-not-allowed disabled:text-neutral-500"
                                             disabled={loading}
                                            >
                                             Reject
                                         </button>
                                     </div>
                                 )}
                            </div>
                            {/* Loan Details */}
                            <p className="text-sm text-neutral-700">
                                Amount: <span className="font-semibold">{formatCurrency(loan.amount)}</span>
                                {loan.status === 'APPROVED' && ` (Balance: ${formatCurrency(loan.remaining_balance || loan.amount)})`}
                            </p>
                            <p className="text-xs text-neutral-500">
                                Rate: {loan.interest_rate}% | Min. Payment: {formatCurrency(loan.minimum_payment)} | Term: {loan.loan_term_months || 'N/A'} mo.
                            </p>
                            <p className="text-xs text-neutral-400 mt-1 truncate">ID: {loan.loan_id}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* --- Form to Apply for New Loan --- */}
            <form onSubmit={handleApplyLoan} className="mt-6 pt-4 border-t border-neutral-200">
                <h4 className="text-md font-semibold text-neutral-700 mb-4">Apply for New Loan</h4>

                {/* Amount Slider Section */}
                <div className="mb-4">
                    <div className="flex justify-between items-center mb-1">
                        <label htmlFor="loanAmountSlider" className="text-sm font-medium text-neutral-600">
                            Loan Amount: <span className="font-bold text-primary-blue">{formatCurrency(newLoanAmount)}</span>
                        </label>
                        <span className="text-sm text-neutral-500">
                            Est. Rate: <span className="font-semibold">{displayRate}%</span>
                        </span>
                    </div>
                    <input
                        id="loanAmountSlider"
                        type="range"
                        min={MIN_LOAN_AMOUNT}
                        max={MAX_LOAN_AMOUNT}
                        step="50" // Adjust step
                        value={newLoanAmount}
                        onChange={(e) => setNewLoanAmount(e.target.value)}
                        disabled={loading}
                        className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer range-lg dark:bg-neutral-700 focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-1"
                    />
                    <div className="flex justify-between text-xs text-neutral-500 mt-1">
                        <span>{formatCurrency(MIN_LOAN_AMOUNT)}</span>
                        <span>{formatCurrency(MAX_LOAN_AMOUNT)}</span>
                    </div>
                </div>

                {/* Submit Button */}
                <div className="text-center mt-5">
                    <button
                        type="submit"
                        disabled={loading} // Only disable based on general loading state
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