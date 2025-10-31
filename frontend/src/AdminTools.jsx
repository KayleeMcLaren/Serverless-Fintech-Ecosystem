import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import { useWallet } from './contexts/WalletContext';
import ConfirmModal from './ConfirmModal';
import { WrenchScrewdriverIcon } from '@heroicons/react/24/outline';

function AdminTools() {
  const { apiUrl } = useWallet();
  const [loading, setLoading] = useState(null); // 'loan-action', 'kyc-action'
  
  // State for Loan Admin
  const [loanIdToManage, setLoanIdToManage] = useState('');
  const [isLoanModalOpen, setIsLoanModalOpen] = useState(false);
  const [loanModalAction, setLoanModalAction] = useState(null);

  // State for Onboarding Admin
  const [userIdToManage, setUserIdToManage] = useState('');
  const [isKycModalOpen, setIsKycModalOpen] = useState(false);
  const [kycModalAction, setKycModalAction] = useState(null);

  // --- Loan Action Handlers ---
  const handleLoanAction = async (loanId, action) => {
    setLoading('loan-action');
    await toast.promise(
      fetch(`${apiUrl}/loan/${encodeURIComponent(loanId)}/${action}`, { method: 'POST' })
        .then(async (response) => {
          const responseBody = await response.json();
          if (!response.ok) throw new Error(responseBody?.message || `HTTP error!`);
          return responseBody;
        }),
      {
        loading: `${action === 'approve' ? 'Approving' : 'Rejecting'} loan...`,
        success: <b>Loan {action === 'approve' ? 'approved' : 'rejected'}!</b>,
        error: (err) => <b>Failed to {action} loan: {err.message}</b>,
      }
    );
    setLoanIdToManage(''); // Clear input on success
    setLoading(null);
  };
  
  const promptLoanAction = (action) => {
    if (!loanIdToManage) { toast.error("Please paste a Loan ID."); return; }
    setLoanModalAction({ loanId: loanIdToManage, action });
    setIsLoanModalOpen(true);
  };
  const handleLoanModalClose = () => setIsLoanModalOpen(false);
  const handleLoanModalConfirm = () => {
    if (loanModalAction) {
      handleLoanAction(loanModalAction.loanId, loanModalAction.action);
    }
    handleLoanModalClose();
  };

  // --- Onboarding Action Handlers ---
  const handleKycAction = async (userId, decision) => {
    setLoading('kyc-action');
    await toast.promise(
      fetch(`${apiUrl}/onboarding/manual-review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, decision: decision }),
      })
      .then(async (response) => {
        const responseBody = await response.json();
        if (!response.ok) throw new Error(responseBody?.message || `HTTP error!`);
        return responseBody;
      }),
      {
        loading: `Submitting manual ${decision}...`,
        success: <b>User {decision.toLowerCase()}!</b>,
        error: (err) => <b>Failed: {err.message}</b>,
      }
    );
    setUserIdToManage(''); // Clear input on success
    setLoading(null);
  };

  const promptKycAction = (decision) => {
    if (!userIdToManage) { toast.error("Please paste a User ID."); return; }
    setKycModalAction({ userId: userIdToManage, decision });
    setIsKycModalOpen(true);
  };
  const handleKycModalClose = () => setIsKycModalOpen(false);
  const handleKycModalConfirm = () => {
    if (kycModalAction) {
      handleKycAction(kycModalAction.userId, kycModalAction.decision);
    }
    handleKycModalClose();
  };


  return (
    <>
      <div className="bg-neutral-800 text-neutral-200 border border-neutral-700 rounded-lg p-6 mt-8 shadow-sm">
        <h2 className="text-xl font-semibold text-white mb-4 text-center flex items-center justify-center gap-2">
            <WrenchScrewdriverIcon className="h-6 w-6" />
            Demo Admin Tools
        </h2>
        
        {/* --- Onboarding Admin --- */}
        <div className="mb-6 pt-4 border-t border-neutral-600">
            <h3 className="text-lg font-semibold text-white mb-2">Onboarding / KYC</h3>
            <p className="text-sm text-neutral-400 text-left mb-4">
                Use this to approve/reject a user stuck in "PENDING_MANUAL_REVIEW" (e.g., from using `flag@example.com`).
            </p>
            <div className="flex flex-wrap gap-3 items-stretch">
                <input
                    type="text"
                    value={userIdToManage}
                    onChange={(e) => setUserIdToManage(e.target.value)}
                    placeholder="Paste User ID from toast"
                    disabled={!!loading}
                    className="flex-grow basis-60 p-2 border border-neutral-600 bg-neutral-700 text-white rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
                />
                <button
                    onClick={() => promptKycAction('APPROVED')}
                    disabled={!!loading || !userIdToManage}
                    className="px-4 py-2 bg-accent-green text-white rounded-md hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-2 disabled:bg-neutral-600 disabled:cursor-not-allowed flex-shrink-0"
                >
                    {loading === 'kyc-action' ? '...' : 'Approve'}
                </button>
                <button
                    onClick={() => promptKycAction('REJECTED')}
                    disabled={!!loading || !userIdToManage}
                    className="px-4 py-2 bg-accent-red text-white rounded-md hover:bg-accent-red-dark focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 disabled:bg-neutral-600 disabled:cursor-not-allowed flex-shrink-0"
                >
                    {loading === 'kyc-action' ? '...' : 'Reject'}
                </button>
            </div>
        </div>

        {/* --- Loan Admin --- */}
        <div className="mb-2 pt-4 border-t border-neutral-600">
            <h3 className="text-lg font-semibold text-white mb-2">Loan Approval</h3>
            <p className="text-sm text-neutral-400 text-left mb-4">
                Use this to approve/reject a 'PENDING' loan from the 'Loans' tab.
            </p>
            <div className="flex flex-wrap gap-3 items-stretch">
                <input
                    type="text"
                    value={loanIdToManage}
                    onChange={(e) => setLoanIdToManage(e.target.value)}
                    placeholder="Paste Loan ID from 'Loans' tab"
                    disabled={!!loading}
                    className="flex-grow basis-60 p-2 border border-neutral-600 bg-neutral-700 text-white rounded-md focus:ring-primary-blue focus:border-primary-blue disabled:opacity-50 min-w-[150px]"
                />
                <button
                    onClick={() => promptLoanAction('approve')}
                    disabled={!!loading || !loanIdToManage}
                    className="px-4 py-2 bg-accent-green text-white rounded-md hover:bg-accent-green-dark focus:outline-none focus:ring-2 focus:ring-accent-green focus:ring-offset-2 disabled:bg-neutral-600 disabled:cursor-not-allowed flex-shrink-0"
                >
                    {loading === 'loan-action' ? '...' : 'Approve'}
                </button>
                <button
                    onClick={() => promptLoanAction('reject')}
                    disabled={!!loading || !loanIdToManage}
                    className="px-4 py-2 bg-accent-red text-white rounded-md hover:bg-accent-red-dark focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 disabled:bg-neutral-600 disabled:cursor-not-allowed flex-shrink-0"
                >
                    {loading === 'loan-action' ? '...' : 'Reject'}
                </button>
            </div>
        </div>
      </div>

      {/* --- Modals --- */}
      <ConfirmModal
        isOpen={isLoanModalOpen}
        onClose={handleLoanModalClose}
        onConfirm={handleLoanModalConfirm}
        title={loanModalAction?.action === 'approve' ? 'Confirm Loan Approval' : 'Confirm Loan Rejection'}
        confirmText={loanModalAction?.action === 'approve' ? 'Approve' : 'Reject'}
        confirmVariant={loanModalAction?.action === 'approve' ? 'primary' : 'danger'}
      >
        Are you sure you want to {loanModalAction?.action} this loan?
      </ConfirmModal>
      
      <ConfirmModal
        isOpen={isKycModalOpen}
        onClose={handleKycModalClose}
        onConfirm={handleKycModalConfirm}
        title={kycModalAction?.decision === 'APPROVED' ? 'Confirm Manual Approval' : 'Confirm Manual Rejection'}
        confirmText={kycModalAction?.decision === 'APPROVED' ? 'Approve User' : 'Reject User'}
        confirmVariant={kycModalAction?.decision === 'APPROVED' ? 'primary' : 'danger'}
      >
        Are you sure you want to manually {kycModalAction?.decision.toLowerCase()} this user's application?
      </ConfirmModal>
    </>
  );
}

export default AdminTools;