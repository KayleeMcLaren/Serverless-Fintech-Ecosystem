import React, { useState } from 'react';
import { Toaster } from 'react-hot-toast';
// Import Components
import SavingsGoals from './SavingsGoals';
import MicroLoans from './MicroLoans';
import PaymentSimulator from './PaymentSimulator';
import DebtOptimiser from './DebtOptimiser';
import Wallet from './Wallet';
import Dashboard from './Dashboard';
import AdminTools from './AdminTools';
import DemoGuide from './DemoGuide';
import Auth from './Auth';
import Spinner from './Spinner';
// Import Icons
import {
  HomeIcon, WalletIcon, BanknotesIcon, CreditCardIcon, 
  ArrowsRightLeftIcon, ScaleIcon, WrenchScrewdriverIcon,
  ArrowRightEndOnRectangleIcon
} from '@heroicons/react/24/outline';
// Import context
import { useWallet } from './contexts/WalletContext';


function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // --- 1. GET isSessionLoading, NOT authLoading ---
  const { wallet, isLoggedIn, isSessionLoading, logOut } = useWallet();

  const renderTabContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />;
      case 'wallet': return <Wallet />;
      case 'savings': return <SavingsGoals />;
      case 'loans': return <MicroLoans />;
      case 'payments': return <PaymentSimulator />;
      case 'optimiser': return <DebtOptimiser />;
      case 'admin': return <AdminTools />;
      default: return null;
    }
  };

  const renderContent = () => {
    // --- 2. CHECK isSessionLoading, NOT authLoading ---
    if (isSessionLoading) {
      return <Spinner />; // Show main spinner *only* while checking session
    }
    
    if (!isLoggedIn) {
      return <Auth />; // Show Login/Sign Up page
    }

    // User is logged in, show the main app
    return (
      <>
        <header className="text-center mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-neutral-800">Serverless Fintech</h1>
          <button
            onClick={logOut}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-neutral-500 hover:text-primary-blue focus:outline-none"
            title="Log Out"
          >
            <ArrowRightEndOnRectangleIcon className="h-5 w-5" />
            <span className="hidden sm:inline">Log Out</span>
          </button>
        </header>

        <nav className="flex flex-wrap justify-center border-b border-neutral-300 mb-8 -space-x-px">
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
              onClick={() => { setActiveTab(tab.id); }}
              className={`flex items-center gap-1.5 py-2 px-3 text-xs sm:text-sm font-medium focus:outline-none whitespace-nowrap border-b-2
                ${activeTab === tab.id
                ? 'border-primary-blue text-primary-blue'
                : 'text-neutral-500 hover:text-neutral-700 hover:border-neutral-300 border-transparent'
              }`}
            >
              <tab.Icon className="h-5 w-5" />
              {tab.label}
            </button>
          ))}
        </nav>

        <main>
          {!wallet && <DemoGuide />}
          {renderTabContent()}
        </main>
      </>
    );
  };
  // --- END WRAPPER ---

  return (
    <div className="max-w-4xl mx-auto my-8 p-8 bg-white rounded-lg shadow-md text-neutral-800">
      <Toaster position="top-center" reverseOrder={false} />
      {renderContent()}
    </div>
  );
}

export default App;