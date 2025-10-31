import React from 'react';
import { InformationCircleIcon } from '@heroicons/react/24/outline';

function DemoGuide() {
  return (
    <div className="bg-blue-50 border border-primary-blue-light rounded-lg p-4 mb-6 text-sm text-primary-blue-dark">
      <div className="flex">
        <div className="flex-shrink-0">
          <InformationCircleIcon className="h-5 w-5 text-primary-blue" aria-hidden="true" />
        </div>
        <div className="ml-3 flex-1 md:flex md:justify-between">
          <div>
            <h4 className="font-semibold">Demo Guide</h4>
            <ul className="list-disc pl-5 mt-2 space-y-1">
              <li>Start by clicking "Apply for Account" on the <b>Wallet</b> tab.</li>
              <li>To test the "manual review" flow, use the email: <b>flag@example.com</b></li>
              <li>To test a credit check rejection, use the email: <b>lowscore@example.com</b></li>
              <li>Use the <b>Admin Tools</b> tab to approve/reject pending applications.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DemoGuide;