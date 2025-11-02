import React, { createContext, useState, useEffect, useContext, useCallback, useRef } from 'react';
import { toast } from 'react-hot-toast';
import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
} from 'amazon-cognito-identity-js';
import { cognitoConfig } from '../cognitoConfig';

const API_URL = import.meta.env.VITE_API_URL;
const LOCAL_STORAGE_KEY = 'fintechWalletId';
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

const userPool = new CognitoUserPool(cognitoConfig);
const WalletContext = createContext();

export const useWallet = () => {
  return useContext(WalletContext);
};

export function WalletProvider({ children }) {
  // --- (State is all correct) ---
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [walletIdInput, setWalletIdInput] = useState('');
  const [amountInput, setAmountInput] = useState('');
  const [transactionCount, setTransactionCount] = useState(0);
  const [emailInput, setEmailInput] = useState('');
  const [onboardingStatus, setOnboardingStatus] = useState(null);
  const pollingInterval = useRef(null);

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isSessionLoading, setIsSessionLoading] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [sessionToken, setSessionToken] = useState(null);

  // --- 1. WRAP getSessionToken in useCallback ---
  const getSessionToken = useCallback(async () => {
    return new Promise((resolve, reject) => {
      const cognitoUser = userPool.getCurrentUser();
      if (!cognitoUser) {
        setIsSessionLoading(false);
        reject(new Error("No user found"));
        return;
      }
      cognitoUser.getSession((err, session) => {
        if (err) {
          setIsSessionLoading(false);
          reject(err);
          return;
        }
        if (session.isValid()) {
          const token = session.getIdToken().getJwtToken();
          setSessionToken(token);
          resolve(token);
        } else {
          setIsSessionLoading(false);
          reject(new Error("Session is not valid"));
        }
      });
    });
  }, []); // Empty array: state setters are stable

  // --- (signUp and confirmSignUp are fine, they are only called by user events) ---
  const signUp = (email, password) => {
    setAuthLoading(true);
    return new Promise((resolve, reject) => {
      userPool.signUp(email, password, null, null, (err, result) => {
        setAuthLoading(false);
        if (err) {
          return reject(err);
        }
        resolve(result);
      });
    });
  };

  const confirmSignUp = (email, code) => {
    setAuthLoading(true);
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({ Username: email, Pool: userPool });
      cognitoUser.confirmRegistration(code, true, (err, result) => {
        setAuthLoading(false);
        if (err) {
          return reject(err);
        }
        resolve(result);
      });
    });
  };

  // --- 2. WRAP logOut in useCallback ---
  const logOut = useCallback(() => {
    const cognitoUser = userPool.getCurrentUser();
    if (cognitoUser) {
      cognitoUser.signOut();
    }
    setIsLoggedIn(false);
    setSessionToken(null);
    setWallet(null);
    setWalletIdInput('');
    localStorage.removeItem(LOCAL_STORAGE_KEY);
  }, []); // Empty array: state setters are stable

  // --- 3. WRAP authorizedFetch in useCallback ---
  const authorizedFetch = useCallback(async (url, options = {}) => {
    let token = sessionToken;
    if (!token) {
      try {
        token = await getSessionToken();
      } catch (err) {
        setIsLoggedIn(false);
        setAuthLoading(false);
        throw new Error("Your session has expired. Please log in again.");
      }
    }
    const headers = { ...options.headers, 'Content-Type': 'application/json', 'Authorization': token };
    const response = await fetch(url, { ...options, headers });
    
    if (response.status === 401 || response.status === 403) {
        logOut(); // Use the memoized logOut
        throw new Error("Authorization failed. Please log in again.");
    }
    return response;
  }, [sessionToken, getSessionToken, logOut]); // Add stable dependencies

  // --- 4. handleFetchWallet is now stable because authorizedFetch is stable ---
  const handleFetchWallet = useCallback(async (idToFetch, isInitialLoad = false) => {
    const walletId = idToFetch || walletIdInput;
    if (!walletId) {
      // toast.error('Please enter a Wallet ID.'); // Removed for auto-fetch
      return Promise.reject(new Error('No Wallet ID provided'));
    }
    setLoading(true);
    if (!isInitialLoad) {
        setWallet(null);
    }
    
    try {
        console.log(`Fetching wallet: ${walletId}`);
        const response = await authorizedFetch(`${API_URL}/wallet/${encodeURIComponent(walletId)}`);
        if (!response.ok) {
           let errorMsg = `HTTP error! Status: ${response.status}`;
           if (response.status === 404) errorMsg = `Wallet ${walletId} not found.`;
           else { try { const errData = await response.json(); errorMsg = errData.message || errorMsg; } catch(e){} }
           throw new Error(errorMsg);
        }
        const data = await response.json();
        setWallet(data);
        localStorage.setItem(LOCAL_STORAGE_KEY, data.wallet_id);
        setWalletIdInput(data.wallet_id);
        console.log('Wallet fetched:', data.wallet_id);
        setTransactionCount(prev => prev + 1);
        return data;
    } catch (e) {
        setWallet(null);
        toast.error(e.message);
        throw e;
    } finally {
        setLoading(false);
    }
  }, [walletIdInput, sessionToken, authorizedFetch]); // This is now correct

  // --- 5. logIn also needs to use the stable handleFetchWallet ---
  const logIn = useCallback((email, password) => {
    setAuthLoading(true);
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({ Username: email, Pool: userPool });
      const authDetails = new AuthenticationDetails({ Username: email, Password: password });

      cognitoUser.authenticateUser(authDetails, {
        onSuccess: (session) => {
          setAuthLoading(false);
          setIsLoggedIn(true);
          const token = session.getIdToken().getJwtToken();
          setSessionToken(token);
          
          const savedWalletId = localStorage.getItem(LOCAL_STORAGE_KEY);
          if (savedWalletId) {
            handleFetchWallet(savedWalletId, true); // Use stable function
          }
          resolve(session);
        },
        onFailure: (err) => {
          setAuthLoading(false);
          reject(err);
        },
      });
    });
  }, [handleFetchWallet]); // Add dependency
  

  // --- 6. This useEffect is now stable and will not cause a loop ---
  useEffect(() => {
    getSessionToken()
      .then(() => {
        setIsLoggedIn(true);
        setIsSessionLoading(false);
        const savedWalletId = localStorage.getItem(LOCAL_STORAGE_KEY);
        if (savedWalletId) {
          setWalletIdInput(savedWalletId);
          handleFetchWallet(savedWalletId, true).catch(err => {
              console.error("Auto-fetch failed:", err.message);
              localStorage.removeItem(LOCAL_STORAGE_KEY);
          });
        }
      })
      .catch(() => {
        setIsLoggedIn(false);
        setIsSessionLoading(false);
      });
  }, [getSessionToken, handleFetchWallet]); // Add getSessionToken


  // Polling function for onboarding
  const pollOnboardingStatus = useCallback((userId) => {
    if (pollingInterval.current) {
      clearInterval(pollingInterval.current);
    }
    const intervalId = setInterval(async () => {
      try {
        const response = await authorizedFetch(`${API_URL}/onboarding/${userId}/status`);
        if (!response.ok) {
          clearInterval(intervalId);
          pollingInterval.current = null;
          toast.error("Failed to get onboarding status.", { id: 'onboarding-toast' });
          setOnboardingStatus('FAILED');
          return;
        }
        const data = await response.json();
        setOnboardingStatus(data.onboarding_status);

        switch (data.onboarding_status) {
          case 'PENDING_ID_VERIFICATION':
            toast.loading('Step 1: Verifying identity...', { id: 'onboarding-toast' });
            break;
          case 'PENDING_MANUAL_REVIEW':
            toast.loading('Step 2: Flagged for manual review. (Use Admin Tools tab)', { id: 'onboarding-toast' });
            break;
          case 'PENDING_CREDIT_CHECK':
            toast.loading('Step 3: Running credit check...', { id: 'onboarding-toast' });
            break;
          case 'PENDING_PROVISIONING':
            toast.loading('Step 4: Provisioning account...', { id: 'onboarding-toast' });
            break;
          case 'APPROVED':
            clearInterval(intervalId);
            pollingInterval.current = null;
            toast.success('Account approved! Wallet created.', { id: 'onboarding-toast' });
            if (data.wallet_id) {
              handleFetchWallet(data.wallet_id, true);
            }
            setOnboardingStatus(null);
            setEmailInput('');
            break;
          case 'REJECTED':
          case 'REJECTED_CREDIT':
          case 'REJECTED_MANUAL':
            clearInterval(intervalId);
            pollingInterval.current = null;
            toast.error('Application was rejected.', { id: 'onboarding-toast' });
            setOnboardingStatus(null);
            break;
        }
      } catch (err) {
        clearInterval(intervalId);
        pollingInterval.current = null;
        toast.error(`Polling error: ${err.message}`, { id: 'onboarding-toast' });
        setOnboardingStatus(null);
      }
    }, 5000);
    pollingInterval.current = intervalId;
  }, [authorizedFetch, handleFetchWallet]); // Add dependencies
  
  // Apply for account
  const handleApplyForAccount = useCallback(async () => {
    if (!emailInput || !emailInput.includes('@')) {
        toast.error("Please enter a valid email address.");
        return;
    }
    setLoading(true);
    setOnboardingStatus('SUBMITTED');
    const toastId = toast.loading('Submitting application...');

    try {
      const response = await authorizedFetch(`${API_URL}/onboarding/start`, {
          method: 'POST',
          body: JSON.stringify({ email: emailInput }),
      });
      const data = await response.json();
      if (!response.ok) {
          throw new Error(data.message || 'Failed to start application.');
      }
      toast.loading('Step 1: Verifying identity...', { id: 'onboarding-toast' });
      pollOnboardingStatus(data.user_id);
    } catch (err) {
      toast.error(`Application failed: ${err.message}`, { id: 'onboarding-toast' });
      setOnboardingStatus(null);
    } finally {
      setLoading(false);
      toast.dismiss(toastId);
    }
  }, [emailInput, authorizedFetch, pollOnboardingStatus]); // Add dependencies
  
  // Refresh function
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
  }, [walletIdInput, handleFetchWallet]); // Add dependency

  // Wallet credit/debit
  const handleTransaction = useCallback(async (type) => {
    const amount = parseFloat(String(amountInput).trim());
    setLoading(true);
    await toast.promise(
       authorizedFetch(
        `${API_URL}/wallet/${encodeURIComponent(wallet.wallet_id)}/${type}`,
        {
          method: 'POST',
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
           refreshWalletAndHistory();
           return <b>Transaction successful! New balance: {formatCurrency(responseBody.balance)}</b>;
        },
        error: (err) => <b>{`Failed to ${type}: ${err.message}`}</b>,
      }
    );
    setLoading(false);
  }, [amountInput, wallet, authorizedFetch, refreshWalletAndHistory]); // Add dependencies

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
    handleApplyForAccount,
    handleFetchWallet,
    handleTransaction,
    refreshWalletAndHistory,
    apiUrl: API_URL,
    
    // Auth values
    isLoggedIn,
    isSessionLoading,
    authLoading,
    signUp,
    confirmSignUp,
    logIn,
    logOut,
    authorizedFetch
  };

  return (
    <WalletContext.Provider value={value}>
      {children}
    </WalletContext.Provider>
  );
}

// Re-export formatCurrency
export { formatCurrency };