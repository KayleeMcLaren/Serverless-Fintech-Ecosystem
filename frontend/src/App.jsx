import React, { useState } from 'react';
import { Toaster, toast } from 'react-hot-toast';
// Import Components
import SavingsGoals from './SavingsGoals';
import MicroLoans from './MicroLoans';
import PaymentSimulator from './PaymentSimulator';
import DebtOptimiser from './DebtOptimiser';
import Wallet from './Wallet';
import Dashboard from './Dashboard';
import AdminTools from './AdminTools'; // <-- 1. IMPORT ADMIN
import DemoGuide from './DemoGuide';   // <-- 2. IMPORT GUIDE
// Import Icons
import {
  HomeIcon, WalletIcon, BanknotesIcon, CreditCardIcon, 
  ArrowsRightLeftIcon, ScaleIcon, WrenchScrewdriverIcon // <-- 3. IMPORT NEW ICON
} from '@heroicons/react/24/outline';
// Import context
import { useWallet } from './contexts/WalletContext';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  // Error state is now managed *per component* or via toasts
  // We can add a global error here if needed, but let's rely on toasts for now.
  // const [error, setError] = useState(null); 

  // --- Get ALL wallet state and functions from the context ---
  const {
    wallet,
    walletIdInput,
    setWalletIdInput,
    amountInput,
    setAmountInput,
    loading,
    transactionCount,
    handleCreateWallet,
    handleFetchWallet, // The silent fetch
    handleTransaction,
    apiUrl,
  } = useWallet();
  // --- End Get State ---


  // --- Wrapper for Fetch Wallet Button Click ---
  // This function adds the toast.promise wrapper to the silent fetch function
  const onFetchClick = () => {
    toast.promise(
        handleFetchWallet(walletIdInput), // Call the function from context
        {
            loading: 'Fetching wallet...',
            success: (data) => <b>Wallet {data.wallet_id.substring(0,8)}... loaded!</b>,
            error: (err) => <b>{err.message}</b>, // Error is already set inline
        }
    ).catch(() => {}); // Catch the re-thrown error so it doesn't log to console
  };
  
  // --- Function to render content based on active tab ---
  const renderTabContent = () => {
    switch (activeTab) {
      case 'dashboard': // --- ADD THIS ---
      return <Dashboard />;
      case 'wallet':
        return <Wallet />;
      case 'savings':
        // No props needed, SavingsGoals will use useWallet()
        return <SavingsGoals />;
      case 'loans':
        // No props needed, MicroLoans will use useWallet()
        return <MicroLoans />;
      case 'payments':
        // No props needed, PaymentSimulator will use useWallet()
        return <PaymentSimulator />;
      case 'optimiser':
        // No props needed, DebtOptimiser will use useWallet()
        return <DebtOptimiser />;
        case 'admin': // <-- 4. ADD ADMIN CASE
        return <AdminTools />;
      default:
        return null;
    }
  };

  // --- Main JSX Structure ---
  return (
    <div className="max-w-4xl mx-auto my-8 p-8 bg-white rounded-lg shadow-md text-neutral-800">
      <Toaster position="top-center" reverseOrder={false} />
      
      <header className="text-center mb-6">
        <h1 className="text-3xl font-bold text-neutral-800">Serverless Fintech Ecosystem</h1>
      </header>

      {/* Tab Navigation */}
      <nav className="flex justify-center border-b border-neutral-300 mb-8 space-x-1 sm:space-x-2">
      {[
        { id: 'dashboard', label: 'Dashboard', Icon: HomeIcon },
        { id: 'wallet', label: 'Wallet', Icon: WalletIcon },
        { id: 'savings', label: 'Savings', Icon: BanknotesIcon },
        { id: 'loans', label: 'Loans', Icon: CreditCardIcon },
        { id: 'payments', label: 'Payments', Icon: ArrowsRightLeftIcon },
        { id: 'optimiser', label: 'Debt Plan', Icon: ScaleIcon },
        { id: 'admin', label: 'Admin Tools', Icon: WrenchScrewdriverIcon },
      ].map((tab) => (
        <button
          key={tab.id}
          onClick={() => { setActiveTab(tab.id); }} // Removed setError
          className={`flex items-center gap-1 sm:gap-1.5 py-2 px-2 sm:px-3 text-xs sm:text-sm font-medium capitalize focus:outline-none whitespace-nowrap ${
            activeTab === tab.id
            ? 'border-b-2 border-primary-blue text-primary-blue'
            : 'text-neutral-500 hover:text-neutral-700 hover:border-neutral-300 border-b-2 border-transparent'
          }`}
        >
          <tab.Icon className="h-4 w-4 sm:h-5 sm:w-5" />
          {tab.label}
        </button>
      ))}
      </nav>

      {/* Main Content Area */}
      <main>
        {/* --- 6. ADD DEMO GUIDE --- */}
        {/* Only show the guide if no wallet is loaded */}
        {!wallet && (
          <DemoGuide />
        )}
        {/* Render the content for the active tab */}
        {renderTabContent()}
      </main>
    </div>
  );
}

export default App;