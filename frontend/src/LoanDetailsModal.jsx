import React from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { useWallet, formatCurrency } from './contexts/WalletContext'; // Correct import

/**
 * A modal to display detailed information about a single loan.
 *
 * @param {object} props
 * @param {object | null} props.loan - The loan object to display. If null, modal is hidden.
 * @param {function} props.onClose - Function to call when closing the modal.
 */
function LoanDetailsModal({ loan, onClose }) {

  if (!loan) {
    return null; // Don't render anything if no loan is selected
  }

  // --- Calculate Progress ---
  const originalAmount = parseFloat(loan.amount || '0');
  const remainingBalance = parseFloat(loan.remaining_balance || '0');
  
  // Calculate amount paid. Ensure it doesn't go below zero if balance is somehow > amount.
  const paidAmount = Math.max(0, originalAmount - remainingBalance);
  // Calculate percentage paid. Avoid division by zero.
  const percentagePaid = originalAmount > 0 ? Math.min((paidAmount / originalAmount) * 100, 100) : 0;
  // ---

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
      aria-modal="true"
      role="dialog"
    >
      {/* Modal Panel */}
      <div
        className="relative w-full max-w-lg p-6 bg-white rounded-lg shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button (X icon) */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 rounded-full text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-400"
          aria-label="Close modal"
        >
          <XMarkIcon className="h-6 w-6" />
        </button>

        {/* Title */}
        <h3 className="text-lg font-semibold text-neutral-800" id="modal-title">
          Loan Details
          <span className={`ml-2 text-sm font-medium px-2.5 py-0.5 rounded ${
              loan.status === 'APPROVED' ? 'bg-accent-green-light text-accent-green-dark' :
              loan.status === 'REJECTED' ? 'bg-accent-red-light text-accent-red-dark' :
              'bg-yellow-100 text-yellow-800'
          }`}>
              {loan.status}
          </span>
        </h3>
        <p className="text-xs text-neutral-400 mt-1 truncate">ID: {loan.loan_id}</p>
        
        {/* --- Progress Bar --- */}
        <div className="mt-4">
            <div className="flex justify-between text-sm font-medium text-neutral-600 mb-1">
                <span>Paid: {formatCurrency(paidAmount)}</span>
                <span>Remaining: {formatCurrency(remainingBalance)}</span>
            </div>
            <div className="w-full bg-neutral-200 rounded-full h-2.5">
                <div
                className="bg-primary-blue h-2.5 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${percentagePaid}%` }}
                ></div>
            </div>
            <div className="text-xs text-neutral-500 text-right mt-1">
                Total: {formatCurrency(originalAmount)}
            </div>
        </div>
        {/* --- End Progress Bar --- */}


        {/* Details Grid */}
        <div className="mt-4 pt-4 border-t border-neutral-200">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2">
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-neutral-500">Interest Rate</dt>
              <dd className="text-md font-semibold text-neutral-900">{loan.interest_rate}%</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-neutral-500">Loan Term</dt>
              <dd className="text-md font-semibold text-neutral-900">{loan.loan_term_months} Months</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-neutral-500">Minimum Payment</dt>
              <dd className="text-md font-semibold text-neutral-900">{formatCurrency(loan.minimum_payment)} / mo</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-neutral-500">Loan Taken</dt>
              <dd className="text-md font-semibold text-neutral-900">{new Date(loan.created_at * 1000).toLocaleDateString()}</dd>
            </div>
          </dl>
        </div>

        {/* Action Button */}
        <div className="mt-6 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-neutral-700 bg-neutral-100 rounded-md border border-neutral-300 hover:bg-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-400 focus:ring-offset-2">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default LoanDetailsModal;