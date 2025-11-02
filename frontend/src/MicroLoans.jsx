import React, { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import Spinner from './Spinner';
import ConfirmModal from './ConfirmModal';
import LoanDetailsModal from './LoanDetailsModal';
import { useWallet, formatCurrency } from './contexts/WalletContext';
import { CurrencyDollarIcon, MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';
import WalletPrompt from './WalletPrompt';

// --- NEW: Combined helper function to get all display values ---
const calculateDisplayValues = (amountStr, termStr) => {
    const P = parseFloat(amountStr || '0');
    const term_months = parseInt(termStr, 10);

    // 1. Calculate Rate (matches backend)
    let annual_rate_val = 10.0;
    if (isNaN(term_months)) {
        // Can't calculate rate or payment without a term
        return { rate: '...', monthlyPayment: 0, totalRepayment: 0 };
    }
    
    if (term_months <= 12) annual_rate_val = 8.0;
    else if (term_months <= 24) annual_rate_val = 12.0;
    else annual_rate_val = 15.0;

    const rate = annual_rate_val.toFixed(1);

    // 2. Calculate Monthly Payment (replicates backend amortization)
    const monthly_rate = (annual_rate_val / 100) / 12;
    const n = term_months;
    let monthlyPayment = 0;

    if (P === 0) {
        return { rate, monthlyPayment: 0, totalRepayment: 0 };
    }
    
    if (monthly_rate === 0) {
        monthlyPayment = P / n;
    } else {
        const numerator = monthly_rate * Math.pow(1 + monthly_rate, n);
        const denominator = Math.pow(1 + monthly_rate, n) - 1;
        monthlyPayment = P * (numerator / denominator);
    }
    
    // 3. Calculate Total Repayment
    const totalRepayment = monthlyPayment * n;

    return { rate, monthlyPayment, totalRepayment };
};
// ---

// --- Constants ---
const MIN_LOAN_AMOUNT = 50;
const MAX_LOAN_AMOUNT = 10000;
const DEFAULT_LOAN_AMOUNT = 1000;
const LOAN_TERMS = [12, 24, 36];
// ---

function MicroLoans() {
    const { wallet, apiUrl, refreshWalletAndHistory, authorizedFetch } = useWallet();
    const walletId = wallet ? wallet.wallet_id : null;

    const [loans, setLoans] = useState([]);
    const [loading, setLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState({});
    const [newLoanAmount, setNewLoanAmount] = useState(String(DEFAULT_LOAN_AMOUNT));
    const [newLoanTerm, setNewLoanTerm] = useState('');
    const [displayRate, setDisplayRate] = useState('...');
    const [displayMonthlyPayment, setDisplayMonthlyPayment] = useState(0);
    const [displayTotalRepayment, setDisplayTotalRepayment] = useState(0);
    const [repayAmount, setRepayAmount] = useState({});
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalAction, setModalAction] = useState(null);
    const [selectedLoan, setSelectedLoan] = useState(null);
    const loanAmountSliderRef = useRef(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeFilter, setActiveFilter] = useState('');
    const [filteredLoans, setFilteredLoans] = useState([]);
    
    // --- Recalculate all display values on change ---
    useEffect(() => {
        const { rate, monthlyPayment, totalRepayment } = calculateDisplayValues(newLoanAmount, newLoanTerm);
        
        setDisplayRate(rate);
        setDisplayMonthlyPayment(monthlyPayment);
        setDisplayTotalRepayment(totalRepayment);
    }, [newLoanAmount, newLoanTerm]);

    // --- Filter loans based on search ---
    useEffect(() => {
        const query = activeFilter.toLowerCase().trim();
        if (!query) {
            setFilteredLoans(loans); // No filter? Show all loans
            return;
        }
        const filtered = loans.filter(loan => {
            const status = loan.status.toLowerCase();
            const loanId = loan.loan_id.toLowerCase();
            return status.includes(query) || loanId.includes(query);
        });
        setFilteredLoans(filtered);
    }, [activeFilter, loans]);

    // --- Search Handlers ---
    const handleSearchSubmit = (e) => {
        e.preventDefault();
        setActiveFilter(searchQuery);
    };

    const handleSearchClear = () => {
        setSearchQuery('');
        setActiveFilter('');
    };

    // --- Fetch Loans ---
    const fetchLoans = useCallback(async () => {
        if (!walletId || !authorizedFetch) {
            setLoans([]);
            return;
        }
        setLoading(true);
        try {
            const response = await authorizedFetch(`${apiUrl}/loan/by-wallet/${encodeURIComponent(walletId)}`);
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
    }, [walletId, apiUrl, authorizedFetch]);

    useEffect(() => {
        fetchLoans();
    }, [fetchLoans]); // Use the memoized fetchLoans function

    // --- Apply for Loan ---
    const handleApplyLoan = async (e) => {
        e.preventDefault();
        const amountNum = parseFloat(newLoanAmount);
        
        if (!walletId || !newLoanAmount || amountNum < MIN_LOAN_AMOUNT || amountNum > MAX_LOAN_AMOUNT) {
            toast.error(`Please select a valid loan amount.`);
            return;
        }
        if (!newLoanTerm) {
            toast.error("Please select a loan term.");
            return;
        }
        
        setLoading(true);
        await toast.promise(
            authorizedFetch(`${apiUrl}/loan`, {
                method: 'POST',
                body: JSON.stringify({
                    wallet_id: walletId,
                    amount: parseFloat(newLoanAmount).toFixed(2),
                    loan_term_months: newLoanTerm
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
                setNewLoanTerm('');
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

    // --- Approve/Reject Loan (used by Admin modal) ---
    const handleLoanAction = async (loanId, action) => {
        setActionLoading(prev => ({ ...prev, [loanId]: true }));

        await toast.promise(
            authorizedFetch(`${apiUrl}/loan/${encodeURIComponent(loanId)}/${action}`, {
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
                fetchLoans(); // Refresh the list
                if (action === 'approve' && refreshWalletAndHistory) {
                    // Give time for the event to process
                    setTimeout(() => {
                        refreshWalletAndHistory(); 
                    }, 4000); 
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

    // --- Handle Repayment ---
    const handleRepayment = async (loanId) => {
        const amountStr = String(repayAmount[loanId] || '').trim();
        if (!amountStr || parseFloat(amountStr) <= 0) {
            toast.error('Please enter a positive repayment amount.');
            return;
        }
        const amount = parseFloat(amountStr).toFixed(2);
        
        setActionLoading(prev => ({ ...prev, [loanId]: true }));

        await toast.promise(
            authorizedFetch(`${apiUrl}/loan/${encodeURIComponent(loanId)}/repay`, {
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
            .then((responseBody) => {
                setRepayAmount(prev => ({ ...prev, [loanId]: '' }));
                setTimeout(() => {
                    fetchLoans();
                    if (refreshWalletAndHistory) {
                        refreshWalletAndHistory();
                    }
                }, 4000);
                return responseBody;
            }),
            {
                loading: 'Processing repayment...',
                success: (responseBody) => <b>Repayment of {formatCurrency(responseBody.amount_processed)} submitted!</b>,
                error: (err) => <b>Repayment failed: {err.message}</b>,
            }
        );
        setActionLoading(prev => ({ ...prev, [loanId]: false }));
    };

    // Helper for repayment input
    const handleRepayAmountChange = (loanId, value) => {
        setRepayAmount(prev => ({ ...prev, [loanId]: value }));
    };

    // --- Modal Helper Functions ---
    const handleModalClose = () => {
        setIsModalOpen(false);
        setModalAction(null);
    };
    const handleModalConfirm = () => {
        if (modalAction) {
            handleLoanAction(modalAction.loanId, modalAction.action);
        }
        handleModalClose();
    };

    // --- Render Logic ---
    if (!walletId) {
        return <WalletPrompt />;
    }

    return (
        <>
            <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
                <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">Micro-Loans</h2>

                {/* --- Search Form --- */}
                <form onSubmit={handleSearchSubmit} className="mb-4 flex gap-2 items-center">
                    <div className="relative flex-grow">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <MagnifyingGlassIcon className="h-5 w-5 text-neutral-400" aria-hidden="true" />
                        </div>
                        <input
                            type="search"
                            name="loanSearch"
                            id="loanSearch"
                            className="block w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-md leading-5 bg-white placeholder-neutral-500 focus:outline-none focus:ring-primary-blue focus:border-primary-blue sm:text-sm"
                            placeholder="Search by status or ID..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    {searchQuery && (
                        <button
                            type="button"
                            onClick={handleSearchClear}
                            className="p-2 text-neutral-500 hover:text-neutral-700"
                            aria-label="Clear search"
                        >
                            <XMarkIcon className="h-5 w-5" />
                        </button>
                    )}
                    <button
                        type="submit"
                        className="px-4 py-2 bg-primary-blue text-white text-sm font-medium rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2"
                    >
                        Search
                    </button>
                </form>

                {loading && !Object.values(actionLoading).some(Boolean) && <Spinner />}
                
                {/* Case 1: No loans at all */}
                {!loading && loans.length === 0 && (
                    <div className="text-center text-neutral-500 my-4 py-8">
                      <CurrencyDollarIcon className="h-12 w-12 mx-auto text-neutral-400" />
                      <h3 className="mt-2 text-sm font-semibold text-neutral-700">No Loans Found</h3>
                      <p className="mt-1 text-sm text-neutral-500">Apply for a new loan using the form below.</p>
                    </div>
                )}

                {/* Case 2: No search results */}
                {!loading && loans.length > 0 && filteredLoans.length === 0 && (
                     <div className="text-center text-neutral-500 my-4 py-8">
                      <MagnifyingGlassIcon className="h-12 w-12 mx-auto text-neutral-400" />
                      <h3 className="mt-2 text-sm font-semibold text-neutral-700">No Loans Match Your Search</h3>
                      <p className="mt-1 text-sm text-neutral-500">Try a different search term.</p>
                    </div>
                )}

                {/* Case 3: Show filtered results */}
                {!loading && filteredLoans.length > 0 && (
                    <div className="space-y-4 mb-6">
                        {filteredLoans.map((loan) => {
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
                                        <button 
                                            onClick={() => setSelectedLoan(loan)}
                                            className="px-2 py-1 bg-neutral-100 text-neutral-700 text-xs rounded hover:bg-neutral-200 border border-neutral-300"
                                        >
                                            Details
                                        </button>
                                    </div>
                                    
                                    {loan.status === 'PENDING' && (
                                         <div className="flex gap-2 mt-2 pt-2 border-t border-neutral-100">
                                             <p className="text-xs text-neutral-500 italic flex-grow">Use Admin Tools tab to approve/reject</p>
                                         </div>
                                     )}
                                     
                                    <p className="text-sm text-neutral-700 mt-2">
                                        Amount: <span className="font-semibold">{formatCurrency(loan.amount)}</span>
                                        {isApproved && ` (Balance: ${formatCurrency(loan.remaining_balance || loan.amount)})`}
                                    </p>
                                    <p className="text-xs text-neutral-500">
                                        Rate: {loan.interest_rate}% | Min. Payment: {formatCurrency(loan.minimum_payment)} | Term: {loan.loan_term_months || 'N/A'} mo.
                                    </p>
                                    <p className="text-xs text-neutral-400 mt-1 truncate">ID: {loan.loan_id}</p>
                                    
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
                            ref={loanAmountSliderRef}
                            type="range" min={MIN_LOAN_AMOUNT} max={MAX_LOAN_AMOUNT} step="50"
                            value={newLoanAmount} onChange={(e) => setNewLoanAmount(e.target.value)}
                            disabled={loading}
                            className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer range-lg focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-1"
                        />
                        <div className="flex justify-between text-xs text-neutral-500 mt-1">
                            <span>{formatCurrency(MIN_LOAN_AMOUNT)}</span>
                            <span>{formatCurrency(MAX_LOAN_AMOUNT)}</span>
                        </div>
                    </div>
                    
                    <div className="mb-4">
                        <label htmlFor="loanTerm" className="block text-sm font-medium text-neutral-600 mb-1">Loan Term</label>
                        <select
                            id="loanTerm"
                            value={newLoanTerm}
                            onChange={(e) => setNewLoanTerm(e.target.value)}
                            disabled={loading}
                            className={`w-full p-2 border rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 ${
                                newLoanTerm ? 'border-neutral-300' : 'border-neutral-300 text-neutral-500'
                            }`}
                            required
                        >
                            <option value="" disabled>-- Select a Term --</option>
                            {LOAN_TERMS.map(term => (
                                <option key={term} value={term}>{term} Months</option>
                            ))}
                        </select>
                    </div>

                    <div className="mb-4 p-4 bg-white border border-neutral-200 rounded-md">
                        <h5 className="text-sm font-medium text-neutral-600 mb-2">Estimated Repayment</h5>
                        <div className="flex justify-between">
                            <span className="text-sm text-neutral-500">Est. Monthly Payment</span>
                            <span className="text-sm font-semibold text-neutral-800">{formatCurrency(displayMonthlyPayment)}</span>
                        </div>
                        <div className="flex justify-between mt-1">
                            <span className="text-sm text-neutral-500">Est. Total Repayment</span>
                            <span className="text-sm font-semibold text-neutral-800">{formatCurrency(displayTotalRepayment)}</span>
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

            {/* --- Confirm Modal (for Admin actions) --- */}
            <ConfirmModal
                isOpen={isModalOpen}
                onClose={handleModalClose}
                onConfirm={handleModalConfirm}
                title={modalAction?.action === 'approve' ? 'Confirm Approval' : 'Confirm Rejection'}
                confirmText={modalAction?.action === 'approve' ? 'Approve' : 'Reject'}
                confirmVariant={modalAction?.action === 'approve' ? 'primary' : 'danger'}
            >
                Are you sure you want to {modalAction?.action} this loan?
                {modalAction?.action === 'approve' && ' This will fund the user\'s wallet.'}
            </ConfirmModal>
            
            <LoanDetailsModal 
                loan={selectedLoan} 
                onClose={() => setSelectedLoan(null)} 
            />
        </> 
    );
}

export default MicroLoans;