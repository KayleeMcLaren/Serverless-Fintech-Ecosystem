import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { toast } from 'react-hot-toast';

// --- Define API URL & Storage Key ---
const API_URL = import.meta.env.VITE_API_URL;
const LOCAL_STORAGE_KEY = 'fintechWalletId';

// --- formatCurrency Helper ---
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

// 1. Create the Context
const WalletContext = createContext();

// 2. Create a custom hook for easy access
export const useWallet = () => {
  return useContext(WalletContext);
};

// 3. Create the Provider Component
export function WalletProvider({ children }) {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [walletIdInput, setWalletIdInput] = useState('');
  const [amountInput, setAmountInput] = useState('');
  const [transactionCount, setTransactionCount] = useState(0); // To trigger history refresh

  // --- NEW: State for onboarding ---
  const [emailInput, setEmailInput] = useState('');
  const [onboardingStatus, setOnboardingStatus] = useState(null);
  // ---

  // --- Wallet Action Functions ---

  const handleFetchWallet = useCallback(async (idToFetch, isInitialLoad = false) => {
    const walletId = idToFetch || walletIdInput;
    if (!walletId) {
      toast.error('Please enter a Wallet ID.');
      return Promise.reject(new Error('No Wallet ID provided'));
    }
    setLoading(true);
    if (!isInitialLoad) {
        setWallet(null);
    }
    
    try {
        console.log(`Fetching wallet: ${walletId}`);
        const response = await fetch(`${API_URL}/wallet/${encodeURIComponent(walletId)}`);
        if (!response.ok) {
           let errorMsg = `HTTP error! Status: ${response.status}`;
           if (response.status === 404) errorMsg = `Wallet ${walletId} not found.`;
           else { try { const errData = await response.json(); errorMsg = errData.message || errorMsg; } catch(e){} }
           throw new Error(errorMsg);
        }
        const data = await response.json();
        setWallet(data);
        if (idToFetch || !wallet) {
           localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet_id);
           setWalletIdInput(data.wallet_id);
        }
        console.log('Wallet fetched:', data.wallet_id);
        setTransactionCount(prev => prev + 1);
        return data;
    } catch (e) {
        setWallet(null);
        throw e;
    } finally {
        setLoading(false);
    }
  }, [walletIdInput, wallet]); // Dependencies are correct

  // Auto-fetch wallet on initial load
  useEffect(() => {
    const savedWalletId = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (savedWalletId) {
      console.log('Found saved wallet ID:', savedWalletId);
      setWalletIdInput(savedWalletId);
      handleFetchWallet(savedWalletId, true).catch(err => {
          console.error("Auto-fetch failed:", err.message);
          localStorage.removeItem(LOCAL_STORAGE_KEY);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run only once on mount

  // --- NEW: Polling function ---
  const pollOnboardingStatus = (userId) => {
    const intervalId = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/onboarding/${userId}/status`);
        if (!response.ok) {
          // Stop polling on a hard error
          clearInterval(intervalId);
          toast.error("Failed to get onboarding status.");
          setOnboardingStatus('FAILED');
          return;
        }
        
        const data = await response.json();
        setOnboardingStatus(data.onboarding_status); // Update status for UI

        switch (data.onboarding_status) {
          case 'PENDING_ID_VERIFICATION':
            toast.loading('Step 1: Verifying identity...', { id: 'onboarding-toast' });
            break;
          case 'PENDING_MANUAL_REVIEW':
            toast.loading('Step 2: Flagged for manual review...', { id: 'onboarding-toast' });
            // In a real app, we'd stop polling here. For the demo, we'll let it continue.
            // You can manually call the 'manual-review' API with Postman to approve it.
            break;
          case 'PENDING_CREDIT_CHECK':
            toast.loading('Step 3: Running credit check...', { id: 'onboarding-toast' });
            break;
          case 'PENDING_PROVISIONING':
            toast.loading('Step 4: Provisioning account...', { id: 'onboarding-toast' });
            break;
          case 'APPROVED':
            clearInterval(intervalId); // Stop polling!
            toast.success('Account approved! Wallet created.', { id: 'onboarding-toast' });
            // The status check now returns the wallet_id
            if (data.wallet_id) {
              handleFetchWallet(data.wallet_id, true); // Fetch the new wallet
            }
            setOnboardingStatus(null);
            setEmailInput(''); // Clear email input
            break;
          case 'REJECTED':
          case 'REJECTED_CREDIT':
          case 'REJECTED_MANUAL':
            clearInterval(intervalId); // Stop polling
            toast.error('Application was rejected.', { id: 'onboarding-toast' });
            setOnboardingStatus(null);
            break;
        }
      } catch (err) {
        clearInterval(intervalId);
        toast.error(`Polling error: ${err.message}`, { id: 'onboarding-toast' });
        setOnboardingStatus(null);
      }
    }, 5000); // Poll every 5 seconds
  };

  // --- UPDATED: handleCreateWallet is now handleApplyForAccount ---
  const handleApplyForAccount = async () => {
    if (!emailInput || !emailInput.includes('@')) {
        toast.error("Please enter a valid email address.");
        return;
    }
    setLoading(true);
    setOnboardingStatus('SUBMITTED');
    const toastId = toast.loading('Submitting application...');

    try {
      const response = await fetch(`${API_URL}/onboarding/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: emailInput }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
          throw new Error(data.message || 'Failed to start application.');
      }
      
      // Start polling
      toast.loading('Step 1: Verifying identity...', { id: 'onboarding-toast' });
      pollOnboardingStatus(data.user_id);
      
    } catch (err) {
      toast.error(`Application failed: ${err.message}`, { id: 'onboarding-toast' });
      setOnboardingStatus(null);
    } finally {
      setLoading(false); // We stop the main 'loading' spinner
      toast.dismiss(toastId); // Dismiss the "Submitting..." toast
    }
  };
  
  // Refresh function that child components can call
  const refreshWalletAndHistory = useCallback(() => {
      console.log("Refreshing wallet balance and transaction history...");
      if (walletIdInput) {
          handleFetchWallet(walletIdInput, true).catch(err => {
              console.error("Wallet refresh failed:", err.message);
              toast.error(`Wallet refresh failed: ${err.message}`);
          });
          setTransactionCount(prev => prev + 1);
      } else {
          console.log("Refresh skipped, no wallet ID input.");
      }
  }, [walletIdInput, handleFetchWallet]); // Added handleFetchWallet to dependencies

  // handleTransaction function (is correct)
  const handleTransaction = async (type) => {
    const amount = parseFloat(String(amountInput).trim());
    setLoading(true);

    await toast.promise(
       fetch(
        `${API_URL}/wallet/${encodeURIComponent(wallet.wallet_id)}/${type}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: amount.toFixed(2) }),
        }
      )
      .then(async (response) => {
       const responseBody = await response.json();
       if (!response.ok) {
          const apiErrorMsg = responseBody?.message || `HTTP error! Status: ${response.status}`;
          throw new Error(apiErrorMsg);
       }
       return responseBody;
    }),
      {
        loading: `${type === 'credit' ? 'Depositing' : 'Withdrawing'}...`,
        success: (responseBody) => {
           setWallet((prevWallet) => ({ ...prevWallet, balance: responseBody.balance }));
           setAmountInput('');
           refreshWalletAndHistory(); // Trigger refresh
           return <b>Transaction successful! New balance: {formatCurrency(responseBody.balance)}</b>;
        },
        error: (err) => <b>{`Failed to ${type}: ${err.message}`}</b>,
      }
    );
    setLoading(false);
  };

  // 4. Value to provide to consumers
  const value = {
    wallet,
    setWallet,
    walletIdInput,
    setWalletIdInput,
    amountInput,
    setAmountInput,
    loading,
    transactionCount,
    emailInput,
    setEmailInput,
    onboardingStatus,
    handleApplyForAccount, // Renamed
    handleFetchWallet,
    handleTransaction,
    refreshWalletAndHistory,
    apiUrl: API_URL,
  };

  return (
    <WalletContext.Provider value={value}>
      {children}
    </WalletContext.Provider>
  );
}

// Re-export formatCurrency if other components need it
export { formatCurrency };