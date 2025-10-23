import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import Spinner from './Spinner';
// Import the context hook and shared helper
import { useWallet, formatCurrency } from './contexts/WalletContext';

// --- Replicate Backend Rate Logic on Frontend ---
const calculateDisplayRate = (amount) => {
    const numAmount = parseFloat(amount || '0');
    if (numAmount < 500) return '25.0';
    if (numAmount < 2000) return '18.5';
    if (numAmount < 5000) return '15.0';
    return '12.5';
};

// --- Define Loan Amount Range ---
const MIN_LOAN_AMOUNT = 50;
const MAX_LOAN_AMOUNT = 10000;
const DEFAULT_LOAN_AMOUNT = 1000;

// Remove props, they will come from context
function MicroLoans() {
    // Get wallet state and functions from context
    const { wallet, apiUrl, refreshWalletAndHistory } = useWallet();
    const walletId = wallet ? wallet.wallet_id : null;

    const [loans, setLoans] = useState([]);
    const [loading, setLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState({});
    const [newLoanAmount, setNewLoanAmount] = useState(String(DEFAULT_LOAN_AMOUNT));
    const [displayRate, setDisplayRate] = useState(calculateDisplayRate(DEFAULT_LOAN_AMOUNT));
    const [repayAmount, setRepayAmount] = useState({});

    // --- Fetch loans when walletId changes ---
    useEffect(() => {
        if (walletId) {
            fetchLoans();
        } else {
            setLoans([]);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [walletId]);

    // --- Recalculate display rate when amount changes ---
    useEffect(() => {
        setDisplayRate(calculateDisplayRate(newLoanAmount));
    }, [newLoanAmount]);

    // --- Fetch Loans (Add Toast on Error) ---
    const fetchLoans = async () => {
        if (!walletId) return;
        setLoading(true);
        try {
            const response = await fetch(`${apiUrl}/loan/by-wallet/${encodeURIComponent(walletId)}`);
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            const data = await response.json();
            data.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
            setLoans(data);
        } catch (e) {
            toast.error(`Fetch loans failed: ${e.message}`);
            setLoans([]);
        } finally {
            setLoading(false);
        }
    };

    // --- Apply for Loan (Use Toast) ---
    const handleApplyLoan = async (e) => {
        e.preventDefault();
        const amountNum = parseFloat(newLoanAmount);
        if (!walletId || !newLoanAmount || amountNum <= 0 || amountNum < MIN_LOAN_AMOUNT || amountNum > MAX_LOAN_AMOUNT) {
            toast.error(`Please select a valid loan amount between ${formatCurrency(MIN_LOAN_AMOUNT)} and ${formatCurrency(MAX_LOAN_AMOUNT)}.`);
            return;
        }
        setLoading(true);

        await toast.promise(
            fetch(`${apiUrl}/loan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    wallet_id: walletId,
                    amount: amountNum.toFixed(2),
                }),
            })
            .then(async (response) => {
                const responseBody = await response.json();
                if (!response.ok) {
                    throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
                }
                return responseBody;
            })
            .then(() => {
                setNewLoanAmount(String(DEFAULT_LOAN_AMOUNT));
                fetchLoans();
            }),
            {
                loading: 'Submitting application...',
                success: <b>Loan application submitted!</b>,
                error: (err) => <b>Application failed: {err.message}</b>,
            }
        );
        setLoading(false);
    };

    // --- Approve/Reject Loan (Use Toast) ---
    const handleLoanAction = async (loanId, action) => {
        if (!window.confirm(`Are you sure you want to ${action} this loan?`)) {
            return;
        }
        setActionLoading(prev => ({ ...prev, [loanId]: true }));
        await toast.promise(
            fetch(`${apiUrl}/loan/${encodeURIComponent(loanId)}/${action}`, {
                method: 'POST',
            })
            .then(async (response) => {
                const responseBody = await response.json();
                if (!response.ok) {
                    const apiErrorMsg = responseBody?.message || `HTTP error! Status: ${response.status}`;
                    throw new Error(apiErrorMsg);
                }
                return responseBody;
            })
            .then(() => {
                fetchLoans();
                // If approving, also refresh main wallet (funds are added)
                if (action === 'approve' && refreshWalletAndHistory) {
                    // Add a delay to allow SNS event to be processed
                    setTimeout(() => {
                        refreshWalletAndHistory();
                    }, 4000); // 4 second delay
                }
            }),
            {
                loading: `${action === 'approve' ? 'Approving' : 'Rejecting'} loan...`,
                success: <b>Loan {action === 'approve' ? 'approved' : 'rejected'}!</b>,
                error: (err) => <b>Failed to {action} loan: {err.message}</b>,
            }
        );
        setActionLoading(prev => ({ ...prev, [loanId]: false }));
    };

    // --- Handle Repayment (Use Toast and Context Refresh) ---
    const handleRepayment = async (loanId) => {
        const amountStr = String(repayAmount[loanId] || '').trim();
        if (!amountStr || parseFloat(amountStr) <= 0) {
            toast.error('Please enter a positive repayment amount.');
            return;
        }
        const amount = parseFloat(amountStr).toFixed(2);
        
        setActionLoading(prev => ({ ...prev, [loanId]: true }));

        await toast.promise(
            fetch(`${apiUrl}/loan/${encodeURIComponent(loanId)}/repay`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount: amount }),
            })
            .then(async (response) => {
                const responseBody = await response.json();
                if (!response.ok) {
                    throw new Error(responseBody?.message || `HTTP error! Status: ${response.status}`);
                }
                return responseBody;
            })
            .then(() => {
                setRepayAmount(prev => ({ ...prev, [loanId]: '' }));
                // Give saga time to run, then refetch
                setTimeout(() => {
                    fetchLoans();
                    // Call parent refresh function from context
                    if (refreshWalletAndHistory) {
                        refreshWalletAndHistory();
                    }
                }, 4000); // 4 second delay for saga (debit + log + update loan)
            }),
            {
                loading: 'Processing repayment...',
                success: <b>Repayment request submitted!</b>,
                error: (err) => <b>Repayment failed: {err.message}</b>,
            }
        );
        setActionLoading(prev => ({ ...prev, [loanId]: false }));
    };

    // Helper for repayment input
    const handleRepayAmountChange = (loanId, value) => {
        setRepayAmount(prev => ({ ...prev, [loanId]: value }));
    };


    // --- Render Logic ---
    if (!walletId) { return null; }

    return (
        <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
            <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Micro-Loans</h2>

            {loading && !Object.values(actionLoading).some(Boolean) && <Spinner />}
            
            {/* --- Display Existing Loans --- */}
            {!loading && loans.length === 0 && (
                <p className="text-center text-neutral-500 my-4">No loans found for this wallet.</p>
            )}
            {!loading && loans.length > 0 && (
                <div className="space-y-4 mb-6">
                    {loans.map((loan) => {
                        const isLoadingThisAction = actionLoading[loan.loan_id];
                        const isApproved = loan.status === 'APPROVED';
                        return (
                            <div key={loan.loan_id} className="p-4 bg-white border border-neutral-200 rounded-md shadow-sm">
                                <div className="flex justify-between items-start mb-2">
                                    <span className={`text-xs font-medium px-2.5 py-0.5 rounded ${
                                        loan.status === 'APPROVED' ? 'bg-accent-green-light text-accent-green-dark' :
                                        loan.status === 'REJECTED' ? 'bg-accent-red-light text-accent-red-dark' :
                                        'bg-yellow-100 text-yellow-800'
                                    }`}>
                                        {loan.status}
                                    </span>
                                    {loan.status === 'PENDING' && (
                                         <div className="flex gap-2">
                                             <button
                                                 onClick={() => handleLoanAction(loan.loan_id, 'approve')}
                                                 className="px-2 py-1 bg-accent-green text-white text-xs rounded hover:bg-accent-green-dark disabled:bg-neutral-300 disabled:cursor-not-allowed disabled:text-neutral-500"
                                                 disabled={isLoadingThisAction || loading}
                                                >
                                                 {isLoadingThisAction ? '...' : 'Approve'}
                                             </button>
                                             <button
                                                 onClick={() => handleLoanAction(loan.loan_id, 'reject')}
                                                 className="px-2 py-1 bg-accent-red text-white text-xs rounded hover:bg-accent-red-dark disabled:bg-neutral-300 disabled:cursor-not-allowed disabled:text-neutral-500"
                                                 disabled={isLoadingThisAction || loading}
                                                >
                                                 {isLoadingThisAction ? '...' : 'Reject'}
                                             </button>
                                         </div>
                                     )}
                                </div>
                                
                                <p className="text-sm text-neutral-700">
                                    Amount: <span className="font-semibold">{formatCurrency(loan.amount)}</span>
                                    {isApproved && ` (Balance: ${formatCurrency(loan.remaining_balance || loan.amount)})`}
                                </p>
                                <p className="text-xs text-neutral-500">
                                    Rate: {loan.interest_rate}% | Min. Payment: {formatCurrency(loan.minimum_payment)} | Term: {loan.loan_term_months || 'N/A'} mo.
                                </p>
                                <p className="text-xs text-neutral-400 mt-1 truncate">ID: {loan.loan_id}</p>

                                {/* --- Repayment Form for APPROVED loans --- */}
                                {isApproved && (
                                    <div className="flex flex-wrap gap-2 items-center mt-3 pt-3 border-t border-neutral-100">
                                        <input
                                            type="number"
                                            placeholder="Repay Amount"
                                            min="0.01"
                                            step="0.01"
                                            value={repayAmount[loan.loan_id] || ''}
                                            onChange={(e) => handleRepayAmountChange(loan.loan_id, e.target.value)}
                                            disabled={loading || isLoadingThisAction}
                                            className="flex-grow basis-28 p-1.5 border border-neutral-300 rounded-md text-sm focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50"
                                        />
                                        <button
                                            onClick={() => handleRepayment(loan.loan_id)}
                                            disabled={loading || isLoadingThisAction || !(repayAmount[loan.loan_id] > 0)}
                                            className="px-3 py-1.5 bg-primary-blue text-white text-xs rounded hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-1 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                                        >
                                            {isLoadingThisAction ? 'Paying...' : 'Make Payment'}
                                        </button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* --- Form to Apply for New Loan --- */}
            <form onSubmit={handleApplyLoan} className="mt-6 pt-4 border-t border-neutral-200">
                <h4 className="text-md font-semibold text-neutral-700 mb-4">Apply for New Loan</h4>
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
                        type="range" min={MIN_LOAN_AMOUNT} max={MAX_LOAN_AMOUNT} step="50"
                        value={newLoanAmount} onChange={(e) => setNewLoanAmount(e.target.value)}
                        disabled={loading}
                        className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer range-lg dark:bg-neutral-700 focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-1"
                    />
                    <div className="flex justify-between text-xs text-neutral-500 mt-1">
                        <span>{formatCurrency(MIN_LOAN_AMOUNT)}</span>
                        <span>{formatCurrency(MAX_LOAN_AMOUNT)}</span>
                    </div>
                </div>
                <div className="text-center mt-5">
                    <button
                        type="submit"
                        disabled={loading}
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