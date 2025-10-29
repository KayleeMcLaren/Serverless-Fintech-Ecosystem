import React from 'react';
import { WalletIcon } from '@heroicons/react/24/outline';

/**
 * A placeholder component shown on tabs when no wallet is loaded.
 * It guides the user to the Wallet tab.
 */
function WalletPrompt() {
  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mt-8 shadow-sm">
      <div className="text-center text-neutral-500 my-4 py-8">
          <WalletIcon className="h-12 w-12 mx-auto text-neutral-400" />
          <h3 className="mt-2 text-sm font-semibold text-neutral-700">No Wallet Loaded</h3>
          <p className="mt-1 text-sm text-neutral-500">
            Please go to the 'Wallet' tab to create or fetch a wallet.
          </p>
      </div>
    </div>
  );
}

export default WalletPrompt;